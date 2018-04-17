program main
    if (omp_get_max_threads() .eq. 2) then
        stop 0
    else
        print *, 'Max threads is', omp_get_max_threads(), 'not 2.'
        stop 1
    endif
end program main
