# -*- coding: utf-8 -*-
try:
    from ultima import *
except ImportError:
    print("cpack.py requires ultima.py to run!")
    exit()

def getProviderListFromArgs(args, parser):
    testProviderList = list()
    for zipFile in args.zip:
        if getFileNameExtension(zipFile) != "zip":
            parser.error("received not zip file")            
        assertFileExist(zipFile) 
        value = (TestFromZipProvider, (zipFile,) )
        testProviderList.append(value)
        
    for folder in args.folder:
        assertFolderExist(folder) 
        value = (TestFromFolderProvider, (folder,) ) 
        testProviderList.append(value)
        
    for generator in args.generator:
        generatorPath = generator[0]
        assertFileExist(generatorPath)
        value = (RandomTestProvider, (generatorPath, args.testname, args.program, "",int(generator[1]))) 
        testProviderList.append(value)
    
    for generator in args.generator2:
        generatorPath = generator[0]
        assertFileExist(generatorPath)
        value = (RandomTestProvider, (generatorPath, args.testname, args.program, generator[2], int(generator[1]))) 
        testProviderList.append(value)


    return testProviderList



def testingLoop(testProviderList, args):
    runner = BasicRunner(args.program)
    runner.ignoreOutput = True
    
    output = zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED, True)


    for testProviderArgs in testProviderList:    
        TestProviderClass = testProviderArgs[0]
        testProviderArgs = testProviderArgs[1]
        print("Procesing tests from \"%s\"" % (testProviderArgs,) )
        testProvider = TestProviderClass(*testProviderArgs)
        
        test_number = 0
        for test in testProvider.getTests():    
            runResult = runner.run(test)         
    
            if runResult.result not in ("OK", "IGNORE"):
                print("Error when doing test %s" % test.testName)
                if args.break_after_error:
                    output.close()
                    tryDeleteFile(args.output)
                    return

            test_number = test_number + 1
            sys.stdout.write("\r%s tests done." % test_number)

            inname = "in/%s.in" % test.testName
            outname = "out/%s.out" % test.testName
            output.writestr(inname, test.inData)
            output.writestr(outname, runResult.outData)




def main():
    parser = argparse.ArgumentParser(description='Runs cpack, program for creating test packages.')
 
    parser.add_argument('program', help='model solution')
    parser.add_argument('testname', help='tests name (ignered in folder and zip sources)')
    parser.add_argument('output', help='output filename')
    
    sourcesGroup = parser.add_argument_group("Test sources")
    sourcesGroup.add_argument('--zip', '-z', help='zip file(s) as test source', nargs='+', default=list())
    sourcesGroup.add_argument('--folder', '-f', help='folder with tests as source', action='append', default=list())
    sourcesGroup.add_argument('--generator', '-g', help='test generator and number of tests to create as test source', nargs=2, metavar=("GEN", "NUM"), action='append', default=list())
    sourcesGroup.add_argument('--generator2', '-g2', help='test generator, number of tests and test name suffix (eg. test123small.in)', nargs=3, metavar=("GEN", "NUM", "SUF"), action='append', default=list())
    
    parser.add_argument('--break_after_error', '-b', help='break pack creating after error, erase half created pack', action='store_false', default=True)

    args = parser.parse_args()    
    assertFileExist(args.program)


    if getFileNameExtension(args.output) != "zip":
        args.output += ".zip"
    
    if os.path.isfile(args.output):
        print("I will not overwrite existing file.")
        return


    providerList = getProviderListFromArgs(args, parser)
    testingLoop(providerList, args)
    

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt - Exiting...")

