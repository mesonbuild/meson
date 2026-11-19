import textwrap

def get_c_code():
    return textwrap.dedent("""\
        int im_going_back_to(void) {
            return 505;
        }
        """)
