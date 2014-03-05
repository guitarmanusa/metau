#include <mp4v2/mp4v2.h>

int main( int argc, char** argv )
{
    if( argc != 2 ) {
        printf( "usage: %s file.mp4\n", argv[0] );
        return 1;
    }

    /* open file for modification */
    MP4FileHandle file = MP4Modify( argv[1], 0 );
    if( file == MP4_INVALID_FILE_HANDLE ) {
        printf( "MP4Modify failed\n" );
        return 1;
    }

    /* Get Chapter information from file */
    MP4Chapter_t *chapterList;
    uint32_t chapterCount;
    MP4ChapterType whatKindOfChapters = MP4GetChapters( file, &chapterList, &chapterCount, MP4ChapterTypeQt );

    if( chapterCount > 0 ){ /* If chapter information is preset */
        int index = 0;
        for(index; index < chapterCount; index++) {
            printf( "%s\t%lu\n", chapterList[index].title, (uint64_t)chapterList[index].duration );
        }
    } else {
        uint64_t total_duration = MP4GetDuration( file );
        uint32_t time_scale = MP4GetTimeScale( file );
        time_scale = time_scale/1000;
        total_duration = total_duration/time_scale;
        printf( "%lu\t%lu\n", total_duration, total_duration );
    }

    MP4Close( file, 0 );

    return 0;
}
