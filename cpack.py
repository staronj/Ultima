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
        value = (TestFromZipProvider, (zipFile,))
        testProviderList.append(value)
        
    for folder in args.folder:
        assertFolderExist(folder) 
        value = (TestFromFolderProvider, (folder,))
        testProviderList.append(value)
        
    for generator in args.generator:
        generatorPath = generator[0]
        assertFileExist(generatorPath)
        value = (RandomTestProvider, (generatorPath, args.testname, args.program, "", int(generator[1])))
        testProviderList.append(value)
    
    for generator in args.generator2:
        generatorPath = generator[0]
        assertFileExist(generatorPath)
        value = (RandomTestProvider, (generatorPath, args.testname, args.program, generator[2], int(generator[1]))) 
        testProviderList.append(value)

    return testProviderList


class TestExecutor(Functor):
    def __init__(self, runner, zip_file, break_after_error):
        Functor.__init__(self)
        self.runner = runner
        self.zip_file = zip_file
        self.break_after_error = break_after_error
        self.keyboard_interrupt_happened = False
        self.should_break = False
        self.done_number = 0
        self.error_number = 0
        self.output_lock = threading.Lock()

    def work(self, test):
        runResult = self.runner.run(test)

        with self.output_lock:
            if runResult.result not in ("OK", "IGNORE"):
                print("Error when doing test %s" % test.testName)
                self.error_number += 1
                if self.break_after_error:
                    return
            else:
                self.done_number += 1

            sys.stdout.write("\r%s tests done, %s errors." % (self.done_number, self.error_number))

            input_name = "in/%s.in" % test.testName
            output_name = "out/%s.out" % test.testName
            self.zip_file.writestr(input_name, test.inputData)
            self.zip_file.writestr(output_name, runResult.outputData)

    def keyboard_interrupt(self):
        print("\nKeyboardInterrupt - going to close...")
        self.keyboard_interrupt_happened = True

    def is_good(self):
        return not self.keyboard_interrupt_happened and not self.should_break


def mainLoop(testProviderList, args):
    runner = BasicRunner(args.program)
    runner.ignoreOutput = True

    zip_file = zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED, True)

    for testProviderArgs in testProviderList:
        TestProviderClass = testProviderArgs[0]
        testProviderArgs = testProviderArgs[1]
        print("Processing tests from \"%s\"" % (testProviderArgs,))
        testProvider = TestProviderClass(*testProviderArgs)

        test_executor = TestExecutor(runner, zip_file, args.break_after_error)
        if args.threads == 1:
            executor = SequentialExecutor(test_executor, testProvider.getTests())
        else:
            executor = ParallelExecutor(test_executor, testProvider.getTests(), args.threads)
        executor.process()


def main():
    parser = argparse.ArgumentParser(description='Runs cpack, program for creating test packages.')
 
    parser.add_argument('program', help='model solution')
    parser.add_argument('testname', help='tests name (ignered in folder and zip sources)')
    parser.add_argument('output', help='output filename')
    
    sourcesGroup = parser.add_argument_group("Test sources")
    sourcesGroup.add_argument('--zip', '-z', help='zip file(s) as test source', nargs='+', default=list())
    sourcesGroup.add_argument('--folder', '-f', help='folder with tests as source', action='append', default=list())
    sourcesGroup.add_argument('--generator', '-g', help='test generator and number of tests to create as test source',
                              nargs=2, metavar=("GEN", "NUM"), action='append', default=list())
    sourcesGroup.add_argument('--generator2', '-g2',
                              help='test generator, number of tests and test name suffix (eg. test123small.in)',
                              nargs=3, metavar=("GEN", "NUM", "SUF"), action='append', default=list())
    
    parser.add_argument('--break_after_error', '-b', help='break pack creating after error, erase half created pack',
                        action='store_false', default=True)

    parser.add_argument('--threads', '-t', help='number of parallel tasks', type=int, default=1)

    args = parser.parse_args()    
    assertFileExist(args.program)

    if getFileNameExtension(args.output) != "zip":
        args.output += ".zip"
    
    if os.path.isfile(args.output):
        print("I will not overwrite existing file.")
        return

    providerList = getProviderListFromArgs(args, parser)
    mainLoop(providerList, args)
    

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt - Exiting...")
