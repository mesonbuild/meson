project('get_all_user_options','cpp')

_cdata = configuration_data()

foreach _opt : get_all_user_options()
    _cdata.set(_opt, get_option(_opt))
endforeach

configure_file(output: 'config.h',
               input: 'config.h.in',
               configuration: _cdata)
