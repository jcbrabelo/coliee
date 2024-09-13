

def coords_before_(before, after):
    return before[0] < after[0] or (before[0] == after[0] and before[1] < after[1])


def range_contains(bigger, smaller):
    return (bigger[0][0] < smaller[0][0] or (bigger[0][0] == smaller[0][0] and bigger[0][1] <= smaller[0][1])) and (bigger[1][0] > smaller[1][0] or (bigger[1][0] == smaller[1][0] and bigger[1][1] >= smaller[1][1]))


def get_num_coords(str_coords):
    parts = str_coords.split('.')
    return (int(parts[0]),int(parts[1]))


def index_to_text_coord(index):
    return '1.0+'+str(index)+'c'