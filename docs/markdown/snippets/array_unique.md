## New `unique()` method on list

List now have a `unique()` method that return a copy of the list without
duplicated elements.

If other lists are provided as arguments to the method, it returns the union
of all lists, without duplicated elements.

```
[1, 1, 2, 2, 3, 3].unique() == [1, 2, 3]
[].unique([1, 2], [2, 3], [3, 4]) == [1, 2, 3, 4]
```
