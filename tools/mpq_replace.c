#include <stdio.h>
#include <StormLib.h>

int main(int argc, char **argv) {
    HANDLE archive = NULL;

    if (argc != 4) {
        fprintf(stderr, "usage: %s <archive.SC2Map> <local-file> <archive-path>\n", argv[0]);
        return 2;
    }

    if (!SFileOpenArchive(argv[1], 0, 0, &archive)) {
        fprintf(stderr, "SFileOpenArchive failed: %lu\n", (unsigned long)SErrGetLastError());
        return 3;
    }

    if (!SFileAddFileEx(
            archive,
            argv[2],
            argv[3],
            MPQ_FILE_REPLACEEXISTING | MPQ_FILE_COMPRESS,
            MPQ_COMPRESSION_ZLIB,
            MPQ_COMPRESSION_NEXT_SAME)) {
        fprintf(stderr, "SFileAddFileEx failed for %s: %lu\n", argv[3], (unsigned long)SErrGetLastError());
        SFileCloseArchive(archive);
        return 4;
    }

    if (!SFileFlushArchive(archive)) {
        fprintf(stderr, "SFileFlushArchive failed: %lu\n", (unsigned long)SErrGetLastError());
        SFileCloseArchive(archive);
        return 5;
    }

    if (!SFileCloseArchive(archive)) {
        fprintf(stderr, "SFileCloseArchive failed: %lu\n", (unsigned long)SErrGetLastError());
        return 6;
    }

    return 0;
}
