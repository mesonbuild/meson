## generator now accepts include_directories objects

These work just like the custom_target ones. Include_directories can be created
at both `generator` creation time, and to the `process()` method, with the
latter having precedent over the former.
