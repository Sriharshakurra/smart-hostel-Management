from hostel.models import Room

def run():
    # Define basic data for 1st floor manually
    base_rooms = {
        101: {'capacity': 3, 'has_attached_washroom': True},
        102: {'capacity': 3, 'has_attached_washroom': True},
        103: {'capacity': 4, 'has_attached_washroom': True},
        104: {'capacity': 1, 'has_attached_washroom': False},
        105: {'capacity': 2, 'has_attached_washroom': True},
        106: {'capacity': 5, 'has_attached_washroom': True},
        107: {'capacity': 1, 'has_attached_washroom': False},
        108: {'capacity': 2, 'has_attached_washroom': True},
        109: {'capacity': 5, 'has_attached_washroom': True},
        110: {'capacity': 2, 'has_attached_washroom': False},
        111: {'capacity': 3, 'has_attached_washroom': True},
        112: {'capacity': 5, 'has_attached_washroom': True},
        113: {'capacity': 1, 'has_attached_washroom': False},
        114: {'capacity': 3, 'has_attached_washroom': True},
    }

    # Copy same pattern for other floors with updated room numbers
    all_rooms = {}
    for floor in range(1, 7):  # Floors 1 to 6
        for base_number, room_info in base_rooms.items():
            new_number = int(str(floor) + str(base_number)[1:])  # e.g., 101 -> 201
            all_rooms[new_number] = {
                'floor': floor,
                'capacity': room_info['capacity'],
                'has_attached_washroom': room_info['has_attached_washroom']
            }

    # Save rooms to DB
    for number, info in all_rooms.items():
        capacity = info['capacity']
        rent = 7000 if capacity == 1 else 6500 if capacity == 2 else 6000 if capacity == 3 else 5500

        Room.objects.update_or_create(
            room_number=number,
            defaults={
                'floor': info['floor'],
                'capacity': capacity,
                'rent': rent,
                'has_attached_washroom': info['has_attached_washroom']
            }
        )
