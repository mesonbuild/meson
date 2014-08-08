MODULE Circle
   REAL, PARAMETER :: Pi = 3.1415927
   REAL :: radius
   INTERFACE DEFAULT
      MODULE PROCEDURE func
   END INTERFACE
   CONTAINS
      FUNCTION func()
         func = 0
      END FUNCTION
END MODULE Circle

PROGRAM PROG
   print *, "Module procedure is working."
END PROGRAM PROG
