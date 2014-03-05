/* This is an example of iTMF Tags convenience API.
 * WARNING: this program will change/destroy many tags in an mp4 file.
 */

#include <mp4v2/mp4v2.h>
#include <stdlib.h>

int main( int argc, char** argv )
{
    if( argc != 3 || ( atoi(argv[2]) != 0 && atoi(argv[2]) != 2 && atoi(argv[2]) != 4 ) ) {
        printf( "usage: %s file.[mp4|m4v|m4a|m4b] rtng\nrtng is either 0 (Inoffensive), 2 (Clean Content) or 4 (Explicit Content)\n", argv[0] );
        return 1;
    }

    /* open file for modification */
    MP4FileHandle file = MP4Modify( argv[1], 0 );
    if( file == MP4_INVALID_FILE_HANDLE ) {
        printf( "MP4Modify failed\n" );
        return 1;
    }

    /* allocate */
    const MP4Tags* tags = MP4TagsAlloc();

    /* fetch data from MP4 file and populate structure */
    MP4TagsFetch( tags, file );

    /* make sure the writing was successful */
    bool successfulWrite = 0;

    /* convert input string to uint8_t */
    const uint8_t rtng = (uint8_t)atoi(argv[2]);

    /* change the rtng atom in memory */
    successfulWrite = MP4TagsSetContentRating( tags, &rtng );

    /* write out tag structure to MP4 file */
    successfulWrite = successfulWrite && MP4TagsStore( tags, file );

    /* free memory associated with structure and close */
    MP4TagsFree( tags );
    MP4Close( file, 0 );

    /* if write was uncessful, return error code */
    if( !successfulWrite ){
        return 1;
    }

    return 0;
}
