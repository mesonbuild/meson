## Logical operators on `feature` objects

It is now possible to apply `and`, `or`, and `not` operators on `feature` objects.

`not` operator returns a `feature` that is 'disabled' if it was 'enabled' or 'auto',
and 'auto' if it was 'disabled'.

`and` operator returns an 'auto' feature if both sides are 'auto`,
'disabled' if any is 'disabled', or 'enabled' if both are 'enabled' or 'auto'.

`or` operator returns 'disabled' if both sides are 'disabled',
'enabled' if any is 'enabled', or 'auto' if both are 'auto' or 'disabled'.

This allow to derive features based on other features, like:

```
feat_a_or_b = get_option('feature_a') or get_option('feature_b')
```
