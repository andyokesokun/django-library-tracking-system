import random
rand_list = [ random.randint(1,20) for x in range(0,10)]

list_comprehension_below_10 = [x for x in range(0,10)]

list_comprehension_below_10 = [x for x in range(0,20)]
filtered_list = filter(lambda x: x < 10, list_comprehension_below_10,)

for item in filtered_list: 
    print(item)