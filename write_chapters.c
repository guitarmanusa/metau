#include <mp4v2/mp4v2.h>
#include <string.h>

int main( int argc, char** argv )
{
    if( argc < 4 || strcmp( argv[2], "-n" ) ) {
        printf( "usage: %s file.mp4 -n numChaps [-t \"Title\" -d msec]...\n", argv[0] );
        return 1;
    }

    /* open file for modification */
    MP4FileHandle file = MP4Modify( argv[1], 0 );
    if( file == MP4_INVALID_FILE_HANDLE ) {
        printf( "MP4Modify failed opening %s\n", argv[1] );
        return 1;
    }

    /* Get Chapter information from file */
    uint32_t chapterCount = atoi( argv[3] );
    MP4Chapter_t chapterList[(int)chapterCount];
    int total_argc_reqd = (int)chapterCount * 4;
    total_argc_reqd += 4;
    int array_index = 0;

    if( argc == total_argc_reqd ){ /* If chapter information is preset on cmd line */
        int index = 4;
        for(index; index < total_argc_reqd; index += 4) {
            if ( strcmp(argv[index],"-t") || strcmp(argv[index+2],"-d")) {
                printf( "Improperly formatted chapter \"%s %s %s %s\"\n", argv[index], argv[index+1], argv[index+2], argv[index+3] );
                return 1;
            }
            chapterList[array_index].duration = (uint32_t)atoi(argv[index+3]);
            strcpy( &chapterList[array_index++].title, argv[index+1] );
            //printf( "%s\t%lu\n", argv[index+1], (uint64_t)atoi(argv[index+3]) );
        }
    } else {
        printf( "Need %d arguments, not %d for %d chapter[s]\n", total_argc_reqd, argc,  (int)chapterCount );
    }

    if ( MP4ChapterTypeQt != MP4SetChapters( file, chapterList, chapterCount, MP4ChapterTypeQt ) ){
        printf( "MP4SetChapters failed." );
    }

    MP4Close( file, 0 );

    printf( "Success!\n" );

    return 0;
}
