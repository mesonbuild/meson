find_package(ZLIB)

if(ZLIB_FOUND OR ZLIB_Found)
  set(SomethingLikeZLIB_FOUND        ON)
  set(SomethingLikeZLIB_LIBRARIES    ${ZLIB_LIBRARY})
  set(SomethingLikeZLIB_INCLUDE_DIRS ${ZLIB_INCLUDE_DIR})
else()
  set(SomethingLikeZLIB_FOUND       OFF)
endif()
