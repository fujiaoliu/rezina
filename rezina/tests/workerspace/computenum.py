#!/use/bin/env python


def get_nums(num):
    return [{'item': i} for i in range(num)]


def cacl_pow(data):
    data['item'] = pow(data['item'], 2)
    return data


def add_one(data):
    data['item'] += 1
    return data
