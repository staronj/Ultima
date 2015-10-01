# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import time
import threading
import zipfile
import re
import io
import collections
import argparse
import importlib

"""
Ultima - script for testing programs in programing contests.
Jakub Staroń, 2013 - 2015, for Surykatki FTW
"""

if sys.version_info < (3, 0):
    print("Python version should be 3.0 or more.")
    exit()


def compareStreams(stream1, stream2):
    """Checks, if streams are the same within the meaning of OI comparator."""
    result = True
    while True:
        line1 = stream1.readline()
        line2 = stream2.readline()    
        if not line1 and not line2:
            break
        
        if line1.split() != line2.split():
            result = False
            break
        
    return result


def advancedCompareStreams(compared, model):
    """
    Compare two streams and return couple (message, different_line)
    If streams are the same, return none
    """
    
    def compareLines(compared_line, model_line):
        length = min(len(model_line), len(compared_line))
        for i in range(0, length):
            if compared_line[i] != model_line[i]:
                return i            
        return None

    line = 1
    while True:
        comparedLine = compared.readline().split()
        modelLine = model.readline().split()
        if not comparedLine and not modelLine:
            return None

        cmpResult = compareLines(comparedLine, modelLine)
        if cmpResult is not None:
            message = "Line %s: read %s expected %s" % (line,
                                                        comparedLine[cmpResult].decode(),
                                                        modelLine[cmpResult].decode())
            return message, line

        if len(comparedLine) < len(modelLine):
            message = "Line %s: end of line, expected %s" % (line, modelLine[len(comparedLine)].decode())
            return message, line

        elif len(comparedLine) > len(modelLine):
            message = "Line %s: rubbish at the end of line." % line
            return message, line

        line += 1


def _resultCheck(_, outputStream, modelOutputStream):
    return compareStreams(outputStream, modelOutputStream)


def _advancedResultCheck(_, outputStream, modelOutputStream):
    return advancedCompareStreams(outputStream, modelOutputStream)[0]


resultCheck = _resultCheck
advancedResultCheck = _advancedResultCheck


def replaceExtension(filename, newExtension):
    """
    Returns filename with changed extension.
    newExtension could be with "dot" or without.    
    """
    newExtension = '.' + newExtension.lstrip(".")
    base = os.path.splitext(filename)[0]
    return base + newExtension


def getFileNameExtension(filename):
    """Returns filename extension (without dot)"""
    return os.path.splitext(filename)[1][1:].lower()


def getFilesFromFolder(folder, extensions=None, subdirectories=False):
    """
    Returns list of files from given folder which have
    given extension or extensions. Default returns list of all files.
    """
    if isinstance(extensions, str):
        extensions = (extensions,)
    
    filesList = list()
    if subdirectories:
        for path, _, files in os.walk(folder):
            for name in files:
                filesList.append(os.path.join(path, name))
    else:
        filesList = [os.path.join(folder, file)
                     for file in os.listdir(folder)
                     if os.path.isfile(os.path.join(folder, file))]
    
    if extensions is not None:
        filesList = [file
                     for file in filesList
                     if getFileNameExtension(file) in extensions]
    
    return filesList


class AsynchronousStreamRelay(threading.Thread):
    def __init__(self, sourceStream, sinkStream, closeStreamAfterDone=True):
        assert callable(sourceStream.read)
        assert callable(sinkStream.write)
        threading.Thread.__init__(self)
        self.sourceStream = sourceStream
        self.sinkStream = sinkStream
        self.chunkSize = 1024
        self.closeStreamAfterDone = closeStreamAfterDone
        
    def run(self):
        try:
            chunk = self.readChunk()
            while chunk:
                self.sinkStream.write(chunk)
                chunk = self.readChunk()
                
            if self.closeStreamAfterDone:   
                self.sinkStream.close()
        except IOError:
            pass

    def readChunk(self):
        return self.sourceStream.read(self.chunkSize)


def callProcess(commandLine, inputStream, outputStream, timeLimit=float("inf")):
    def timeLimiter(processHandle):
        pollSeconds = 0.001
        startTime = time.time()
        deadline = startTime + timeLimit    
        while time.time() < deadline and processHandle.poll() is None:
            time.sleep(pollSeconds)
        processExecutionTime = time.time() - startTime
        if processHandle.poll() is None:
            process.terminate()        
        processHandle.wait()
        return processExecutionTime
  
    if isinstance(commandLine, str):
        commandLine = (commandLine,)
        
    if getFileNameExtension(commandLine[0]) == 'py':
        commandLine = (sys.executable,) + commandLine

    popenArgs = {'args': commandLine, 'stdin': subprocess.PIPE, 'stdout': subprocess.PIPE}
    process = subprocess.Popen(**popenArgs)
        
    stdin_writer = AsynchronousStreamRelay(inputStream, process.stdin)
    stdin_writer.start()
    stdout_reader = AsynchronousStreamRelay(process.stdout, outputStream, False)
    stdout_reader.start()

    processTime = timeLimiter(process)
   
    stdin_writer.join()    
    stdout_reader.join()    
    process.stdout.close()   
   
    return process.poll(), processTime


def createFolder(folderName):
    """Creates folder. If folder exists, does nothing."""
    if not os.path.exists(folderName):
        os.makedirs(folderName)


def waitForKey():
    input("Press Enter to continue...")    


def assertFileExist(filename):
    if not os.path.isfile(filename):
        print("File not found %s" % os.path.basename(filename))
        waitForKey()
        exit()


def assertFolderExist(folder_name):
    if not os.path.isdir(folder_name):
        print("Folder not found %s" % os.path.basename(folder_name))
        waitForKey()
        exit()


def saveToFile(string, filename):
    try:
        with open(filename, "wb") as fileHandle:
            fileHandle.write(string)
    except IOError:
        print("Error when writing to file %s" % filename)


def tryDeleteFile(filename):
    try:
        os.remove(filename)
        return True
    except OSError:
        return False


def splitTestName(test_name):
    """
    Divide test_name in tuple (name, number, text after number).
    If pattern can't be matched, tre tuple (testname, "","") is returned.
    test_name must be string
    """
    if not hasattr(splitTestName, "pattern"):
        splitTestName.pattern = re.compile("^([a-zA-Z_]+)(\d+)([a-zA-Z]*)")
        
    found = splitTestName.pattern.search(test_name)
    if found is None:
        return test_name, 0, ""
    else:
        result = found.groups()
        return result[0], int(result[1]), result[2]


class Test:
    def __init__(self, testName):
        self.testName = testName
        self._inputData = None
        self._modelOutputData = None

    @property
    def haveModelOutput(self):
        raise NotImplementedError()
       
    @property
    def inputStream(self):
        return io.BytesIO(self.inputData)
    
    @property
    def modelOutputStream(self):
        return io.BytesIO(self.modelOutputData)
    
    @property
    def inputData(self):
        if self._inputData is None:
            self._inputData = self._generateInputData()
        return self._inputData
    
    @property
    def modelOutputData(self):
        if not self.haveModelOutput:
            raise Exception("Test don't have model out!")
            
        if self._modelOutputData is None:
            self._modelOutputData = self._generateModelOutputData()
        return self._modelOutputData

    def _generateInputData(self):
        """Should generate input data.
        Function must be overwritten in inheriting class.
        Function should generate input data,
        ie read from a file, run generator.
        It's guaranteed, that it will be called only once
        and result will be cached.
        """
        raise NotImplementedError()

    def _generateModelOutputData(self):
        """Should generate output data.
        Function must be overwritten in inheriting class.
        Function should generate model output data,
        ie read from a file, run model solution.
        It's guaranteed, that it will be called only once
        and result will be cached.
        """
        raise NotImplementedError()

    def saveInputData(self, folder="."):
        assertFolderExist(folder)
        filename = "%s.in" % self.testName
        saveToFile(self.inputData, os.path.join(folder, filename))
        
    def saveModelOutputData(self, folder="."):
        assertFolderExist(folder)
        filename = "%s.out" % self.testName
        saveToFile(self.modelOutputData, os.path.join(folder, filename))
    

class TestProvider:
    def getTests(self):
        raise NotImplementedError()

    @staticmethod
    def sortTests(testList):
        assert isinstance(testList, list)

        def splitTestPath(testName):
            return splitTestName(os.path.basename(testName))
        testList.sort(key=lambda testName: splitTestPath(testName))
        testList.sort(key=lambda testName: not splitTestPath(testName)[2] == "ocen")

    @staticmethod
    def onlyWithExtension(testList, extension):
        assert isinstance(extension, str)
        assert isinstance(testList, list)
        return [filename for filename in testList if getFileNameExtension(os.path.basename(filename)) == extension]

    @staticmethod
    def getOutFilePath(inFilePath):
        modelOutFilePath = re.sub(r'\.in$', r'.out', inFilePath, flags=re.IGNORECASE)
        modelOutFilePath = re.sub(r'^in(?=[/\\])', r'out', modelOutFilePath)
        modelOutFilePath = re.sub(r'([/\\])in(?=[/\\])', r'\1out', modelOutFilePath) 
        return modelOutFilePath
        
 
class TestFromFolder(Test):
    def __init__(self, inFilename, modelOutFilename):
        self.inFilename = inFilename
        self.modelOutFilename = modelOutFilename
        inFilenameBasename = os.path.basename(inFilename)
        testName = os.path.splitext(inFilenameBasename)[0]
        Test.__init__(self, testName)
    
    @property
    def haveModelOutput(self):
        return self.modelOutFilename is not None
    
    def _generateInputData(self):
        with open(self.inFilename, 'rb') as inFile:
            return inFile.read()
    
    def _generateModelOutputData(self):
        with open(self.modelOutFilename, 'rb') as modelOutFile:
            return modelOutFile.read()
  

class TestFromFolderProvider(TestProvider):
    def __init__(self, folderPath):
        self.folderPath = folderPath
        self.fileInList = getFilesFromFolder(folderPath, "in", subdirectories=True)
              
        self.sortTests(self.fileInList)
    
    def getTests(self):
        for inFile in self.fileInList:
            modelOutFile = self.getOutFilePath(inFile)
            
            if not os.path.isfile(modelOutFile):
                modelOutFile = None
                
            yield TestFromFolder(inFile, modelOutFile)      


class RandomTest(Test):
    def __init__(self, generatorPath, testNumber, testNamePrefix="random", modelSolutionPath=None, testNameSuffix=""):
        assertFileExist(generatorPath)
        if modelSolutionPath is not None:
            assertFileExist(modelSolutionPath)

        testName = "%s%s%s" % (testNamePrefix, testNumber, testNameSuffix)
        Test.__init__(self, testName)
        self.testNumber = testNumber
        self.generatorPath = generatorPath   
        self.modelSolutionPath = modelSolutionPath    
              
    @property
    def haveModelOutput(self):
        return self.modelSolutionPath is not None
    
    def _generateInputData(self):
        inputStream = io.BytesIO()
        generatorArgsStream = io.BytesIO(str(self.testNumber).encode())
        code, _ = callProcess(self.generatorPath, generatorArgsStream, inputStream)
        
        if code != 0:
            print("\nCritical Error. In generator crash. Exiting.")
            exit()
            
        inputData = inputStream.getvalue()
        if len(inputData) == 0:
            print("\nCritical Error. In generator wrote no output. Exiting.")
            exit()

        return inputData
            
    def _generateModelOutputData(self):
        modelOutputStream = io.BytesIO()
        code, _ = callProcess(self.modelSolutionPath, self.inputStream, modelOutputStream)
        
        if code != 0:
            print("\nCritical Error. Model solution crash. Exiting.")
            exit()
        
        modelOutputData = modelOutputStream.getvalue()
        if len(modelOutputData) == 0:
            print("\nCritical Error. Model wrote no output. Exiting.")
            exit()

        return modelOutputData
    
    
class RandomTestProvider(TestProvider):
    def __init__(self, testGenerator, testName, modelSolutionPath=None, nameSuffix="", testLimit=None):
        assertFileExist(testGenerator)
        if modelSolutionPath is not None:
            assertFileExist(modelSolutionPath)
        self.testGenerator = testGenerator
        self.testName = testName
        self.modelSolutionPath = modelSolutionPath
        self.nameSuffix = nameSuffix
        self.testLimit = testLimit
    
    def getTests(self):
        index = 0
        while True:
            index += 1
            yield RandomTest(self.testGenerator, index, self.testName, self.modelSolutionPath, self.nameSuffix)            
            if self.testLimit is not None and self.testLimit <= index:
                break 


class TestFromZip(Test):
    def __init__(self, zipFile, inFilename, modelOutFilename):
        testBaseName = os.path.basename(inFilename)
        testName = os.path.splitext(testBaseName)[0]
        Test.__init__(self, testName)
        self.zipFile = zipFile
        self.inFilename = inFilename
        self.modelOutFilename = modelOutFilename

    @property  
    def haveModelOutput(self):
        return self.modelOutFilename is not None
    
    def _generateInputData(self):
        with self.zipFile.open(self.inFilename, 'r') as fileInputData:
            return fileInputData.read()
        
    def _generateModelOutputData(self):
        with self.zipFile.open(self.modelOutFilename, 'r') as fileModelOutputData:
            return fileModelOutputData.read()


class TestFromZipProvider(TestProvider):
    def __init__(self, filename):
        assertFileExist(filename)
        self.zipFile = zipfile.ZipFile(filename)
        if self.zipFile.testzip() is not None:
            raise zipfile.BadZipfile()
        
        namelist = self.zipFile.namelist()
           
        self.fileInList = self.onlyWithExtension(namelist, "in")
        self.fileOutList = self.onlyWithExtension(namelist, "out")                
        self.fileOutList = set(self.fileOutList)
        self.sortTests(self.fileInList)        
        
    def getTests(self):
        for filename in self.fileInList:  
            modelOutFile = self.getOutFilePath(filename)
                        
            if modelOutFile not in self.fileOutList:
                modelOutFile = None
                
            yield TestFromZip(self.zipFile, filename, modelOutFile)   


class RunResult:
    def __init__(self):
        self.returnCode = None
        self.processTime = None
        self.result = None
        self.outputData = b""
        
    @property
    def outputStream(self):
        return io.BytesIO(self.outputData)
    

class BasicRunner:
    def __init__(self, programName):
        assertFileExist(programName)            
        self.programName = programName
        self.timeLimit = 10
        self.ignoreOutput = False
    
    def run(self, test):
        return self.doRun(self.programName, test)
    
    def doRun(self, command, test):
        runResult = RunResult()
        outputStream = io.BytesIO()
        runResult.returnCode, runResult.processTime = callProcess(command, test.inputStream, outputStream, self.timeLimit)
        runResult.outputData = outputStream.getvalue()
        
        runResult.result = "OK"
        if runResult.processTime >= self.timeLimit:
            runResult.result = "TLE"
        elif runResult.returnCode != 0:
            runResult.result = "RE"
        elif self.ignoreOutput:
            runResult.result = "IGNORE"
        elif len(runResult.outputData) == 0:
            runResult.result = "NF"
        elif not test.haveModelOutput:
            runResult.result = "NOMODEL"        
        elif not resultCheck(test.inputStream, runResult.outputStream, test.modelOutputStream):
            runResult.result = "WA"                  
                    
        return runResult
    
     
class OITimeToolRunner(BasicRunner):
    def __init__(self, programName, oitimetoolPath=""):
        BasicRunner.__init__(self, programName)

        self.timeLimit = 30
        self.oitimetoolDllPath = "oitimetool\oitimetool.dll"
        self.pinPath = "oitimetool\pin\pin.exe"
        self.oitimetoolDllPath = os.path.join(oitimetoolPath, self.oitimetoolDllPath)
        self.pinPath = os.path.join(oitimetoolPath, self.pinPath)
        self.oitimetoolCommand = (self.pinPath, "-t", self.oitimetoolDllPath, "--", self.programName)

        assertFileExist(self.oitimetoolDllPath)
        assertFileExist(self.pinPath)
        
    def run(self, test):
        return self.doRun(self.oitimetoolCommand, test)


class TestCounter:
    def __init__(self):
        self.queue = collections.deque()
    
    def rate(self):
        timeRange = (time.time() - self.queue[0])
        if timeRange == 0:
            return 0
        else:
            return len(self.queue) / timeRange
    
    def testDone(self):
        self.queue.append(time.time())
        while len(self.queue) >= 10:
            self.queue.popleft()


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
        
    if args.generator is not None:
        assertFileExist(args.generator[0])
        assertFileExist(args.generator[1])
        generatorPath = args.generator[0]
        modelPath = args.generator[1]
        testName = os.path.splitext(args.program)[0]
        value = (RandomTestProvider, (generatorPath, testName, modelPath))
        testProviderList.append(value)
        
    return testProviderList


def getRunnerFromArgs(args):
    if args.oitimetool is not None:
        runner = OITimeToolRunner(args.program, args.oitimetool)
    else:
        runner = BasicRunner(args.program)
    
    runner.ignoreOutput = args.ignore_out
    if args.time_limit is not None:
        runner.timeLimit = args.time_limit
        
    return runner


def testingLoop(testProviderList, runner, args):    
    number_of_fails = 0
    number_of_tests = 0
    for testProviderArgs in testProviderList:    
        TestProviderClass = testProviderArgs[0]
        testProviderArgs = testProviderArgs[1]
        print("Processing tests from \"%s\"" % (testProviderArgs,))
        testProvider = TestProviderClass(*testProviderArgs)
        for test in testProvider.getTests():
            if args.break_after is not None and number_of_fails >= args.break_after:
                return
            
            if args.tests_limit is not None and number_of_tests >= args.tests_limit:
                return
            
            if args.keyword is not None and test.testName.find(args.keyword) == -1:
                continue
                        
            sys.stdout.write("%s " % test.testName)
            sys.stdout.flush()
            runResult = runner.run(test)         
    
            print("%s, time: %.2f sec" % (runResult.result, runResult.processTime))
            
            number_of_tests += 1
            if runResult.result not in ("OK", "IGNORE"):
                number_of_fails += 1
                print(advancedResultCheck(test.inputStream, runResult.outputStream, test.modelOutputStream))
                
                if args.wrong_folder is not None:
                    createFolder(args.wrong_folder)
                    test.saveInputData(folder=args.wrong_folder)
                    test.saveModelOutputData(folder=args.wrong_folder)
                    
                if args.wait_after_error:
                    waitForKey()
                          
            print("------------------------")


def main():
    parser = argparse.ArgumentParser(description='Runs ultima, script for testing programs for OI-like contests.')
 
    parser.add_argument('program', help='program to be tested')
    sourcesGroup = parser.add_argument_group("Test sources")
    sourcesGroup.add_argument('--zip', '-z', help='zip file(s) as test source', nargs='+', default=list())
    sourcesGroup.add_argument('--folder', '-f', help='folder with tests as source', action='append', default=list())
    sourcesGroup.add_argument('--generator', '-g', help='test generator and model solution as test source', nargs=2, metavar=("GEN", "WZO"))
    
    parser.add_argument('--checker', '-c', help='provide your own checking function by python script, file must be in the same folder as ultima script')
    parser.add_argument('--wait_after_error', '-w', help='wait for key after failed test', action='store_true', default=False)
    parser.add_argument('--save_to_folder', '-s', help='save failed tests to specified folder', metavar="FOLDER", dest="wrong_folder")
    parser.add_argument('--ignore_out', '-i', help='ignore program out', action='store_true', default=False)
    parser.add_argument('--time_limit', '-t', help='set execution time limit', type=float)
    parser.add_argument('--oitimetool', '-o', help='use oitimetool, optionally path to oitimetool folder', nargs='?', const="")
    parser.add_argument('--keyword', '-k', help='run only tests with specified keyword in name')
    parser.add_argument('--break_after', '-b', help='break testing after N fails', type=int, metavar='N' )
    parser.add_argument('--tests_limit', '-n', help='run only N first tests', type=int, metavar='N' )
    
    args = parser.parse_args()    
    assertFileExist(args.program)
    testProviderList = getProviderListFromArgs(args, parser)
    runner = getRunnerFromArgs(args)
    
    if args.checker is not None:
        try:
            if getFileNameExtension(args.checker) == 'py':
                args.checker = os.path.splitext(args.checker)[0]

            checker = importlib.import_module(args.checker)
            
            if not hasattr(checker, 'check'):
                print("Module %s don't have check function!" % args.checker)
                exit()

            global resultCheck
            global advancedResultCheck
            resultCheck = lambda inS, outS, modelS: checker.check(inS, outS, modelS) == "OK"
            advancedResultCheck = lambda inS, outS, modelS: checker.check(inS, outS, modelS)
            
        except ImportError:
            print("Could not import %s!" % args.checker)
            exit()

    testingLoop(testProviderList, runner, args)    


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt - Exiting...")
        

