"""Pure exact matching shared by M5 comparison and M5.5 intelligence."""
import json


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def normalize(value):
    return ' '.join(value.split()).casefold()


def keys(values):
    return sorted({normalize(value) for value in values if normalize(value)})


def set_comparison(left, right):
    left, right = set(left), set(right)
    return {'shared': sorted(left & right), 'left_only': sorted(left - right),
            'right_only': sorted(right - left)}
