import sys
import io
import os
import zipfile
import tarfile

def replaceExtension(filename, newExtension):
    """
    Returns filename with changed extension.
    newExtension could be with "dot" or without.    
    """
    newExtension = '.' + newExtension.lstrip(".")
    base = os.path.splitext(filename)[0]
    return (base + newExtension)

def getFileNameExtension(filename):
    """Returns filename extension (without dot)"""
    return os.path.splitext(filename)[1][1:].lower()


def main():
    if len(sys.argv) not in range(2,4) or not os.path.isfile(sys.argv[1]) or getFileNameExtension(sys.argv[1]) != 'tar':
        print("Usage: tar2zip.py TAR_FILE [OUTPUT]")
        return

    source = sys.argv[1]

    if len(sys.argv) == 2:
        sink = replaceExtension(source, "zip")
    else:
        sink = sys.argv[2]

    if getFileNameExtension(sink) != 'zip':
        print("Output must have zip extension!")
        return

    if not tarfile.is_tarfile(source):
        print("%s is not a valid tar file" % source)
        return

    if os.path.isfile(sink):
        print("I will not overwrite existing file!")
        return


    source = tarfile.open(source)
    sink = zipfile.ZipFile(sink, 'w', zipfile.ZIP_DEFLATED, True)

    number_of_files = 0;
    for member in source.getmembers():
        if member.isfile():
            sink.writestr(member.name, source.extractfile(member).read())
            number_of_files = number_of_files + 1
            sys.stdout.write('\r%s files copied.' % number_of_files)

    print("\nSuccesfully done. %s files packed." % number_of_files)
        
if __name__ == "__main__":
    main()
