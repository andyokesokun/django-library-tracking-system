import datetime
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Author, Book, Member, Loan
from .serializers import AuthorSerializer, BookSerializer, MemberSerializer, LoanSerializer, TopActiveMemberSerializer,serializers
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Prefetch
from django.db.models import Count, Q
from .tasks import send_loan_notification

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related('author').prefetch_related(
        Prefetch(
            'loans',
            queryset=Loan.objects.select_related('member__user')
        )
    )
    serializer_class = BookSerializer

    @action(detail=True, methods=['post'])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response({'error': 'No available copies.'}, status=status.HTTP_400_BAD_REQUEST)
        member_id = request.data.get('member_id')
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay(loan.id)
        return Response({'status': 'Book loaned successfully.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get('member_id')
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response({'error': 'Active loan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response({'status': 'Book returned successfully.'}, status=status.HTTP_200_OK)
    

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

    @action(detail=False, methods=['get'], url_path='top-active')
    def top_active(self, request):
        members = (
            Member.objects.annotate(active_loans=Count('loans', filter=Q(loans__is_returned=False)))
            .filter(active_loans__gt=0)
            .order_by('-active_loans')[:5]
        )
        serializer = TopActiveMemberSerializer(members, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class ExtendDueDateSerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1)

class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer

    @action(detail=True, methods=['patch'])
    def extend_due_date(self, request, pk=None):
        loan = self.get_object()

        if loan.return_date < datetime.time():
            Response({'status': 'Book loan date alraedy due'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ExtendDueDateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        days = serializer.validated_data["days"]
        loan.return_date +=timedelta(days)
        loan.save()
        return Response({'additional_days': days}, status=status.HTTP_200_OK)
