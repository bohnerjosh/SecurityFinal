__all__ = ['sorted_iterdir']


def sorted_iterdir(directory):
    return sorted([path for path in directory.iterdir()], key=lambda p: p.name)
