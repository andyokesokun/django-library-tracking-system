from rest_framework import serializers
from .models import Author, Book, Member, Loan
from django.contrib.auth.models import User
from datetime import date, timedelta

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = '__all__'

class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(), source='author', write_only=True
    )

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'author_id', 'isbn', 'genre', 'available_copies']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class TopActiveMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    email = serializers.EmailField(source='user.email')
    active_loans = serializers.IntegerField()

    class Meta:
        model = Member
        fields = ['id', 'username', 'email', 'active_loans']

class MemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = Member
        fields = ['id', 'user', 'user_id', 'membership_date']

class LoanSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(), source='book', write_only=True
    )
    member = MemberSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        queryset=Member.objects.all(), source='member', write_only=True
    )
    
    def create(self, validated_data):
        loan = Loan(**validated_data)
        loan.due_date = loan.loan_date+timedelta(days=14)
        loan.save()
        return loan
        
    class Meta:
        model = Loan
        fields = ['id', 'book', 'book_id', 'member', 'member_id', 'loan_date', 'return_date', 'is_returned']
