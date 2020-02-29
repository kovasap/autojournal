import zlib
import gzip

from dissect import cstruct

data = gzip.open('db_BACKUP_2020_02_15.PT', 'rb').read()

print(data)

# cparser = cstruct.cstruct()
# cparser.load("""
# struct DATABASE {
#   int version;
#   int magic;
#   int numtags;
#   struct { char name[32]; int color; } tags[numtags];
#   int minfilter;
#   int foldlevel;
#   int prefs[10];
#   NODE root;
# };
# 
# struct DAY {
#   unsigned short day;
#   unsigned short firstminuteused;
#   int activeseconds;
#   int semiidleseconds
#   int key;
#   int lmb;
#   int rmb;
#   int scrollwheel;
# };
# 
# struct NODE {
#   char *name;
#   int tagindex;
#   char ishidden;
#   int numberofdays;
#   DAY days[numberofdays];
#   int numchildren;
#   NODE children[numchildren];
# };
# """)
# result = cparser.some_struct(data)
# print(result)


# from cffi import FFI
# ffi = FFI()

# ffi.cdef("""
# typedef struct {
#   int version;
#   int magic;
#   int numtags;
#   struct { char name[32]; int color; } tags[numtags];
#   int minfilter;
#   int foldlevel;
#   int prefs[10];
#   NODE root;
# } DATABASE;
# 
# typedef struct {
#   char *name;
#   int tagindex;
#   char ishidden;
#   int numberofdays;
#   DAY days[numberofdays];
#   int numchildren;
#   NODE children[numchildren];
# } NODE;
# 
# typedef struct {
#   unsigned short day;
#   unsigned short firstminuteused;
#   int activeseconds;
#   int semiidleseconds
#   int key;
#   int lmb;
#   int rmb;
#   int scrollwheel;
# } DAY
# """)
# 
# 
# 
# DATABASE_struct = ffi.new('DATABASE*')
# DATABASE_buffer = ffi.buffer(DATABASE_struct)
# DATABASE_buffer[:] = data
# print(DATABASE_struct)

# compressed_data = open('db_BACKUP_2020_02_15.PT', 'rb').read()
# print(zlib.decompress(compressed_data))
