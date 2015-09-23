# -*- coding: utf-8 -*-
import sys
if sys.version_info < (3, 0):
    print("Python version should be 3.0 or more.")
    exit()

"""
Ultima - script for testing programs in programing contests.
Jakub Staroń, 2013 - 2014, for Surykatki FTW
"""

import os
import subprocess
import time
import threading
import zipfile
import re
import io
import collections

def compareFiles(stream1, stream2): 
    """Checks, if streams are the same within the meaning of OI comparer."""
    result = True
    while(True):
        line1 = stream1.readline()
        line2 = stream2.readline()    
        if not line1 and not line2:
            break
        
        if line1.split() != line2.split():
            result = False
            break
        
    return result


def advencedCompareFiles(compared, model):
    """
    Compare two streams and return couple (message, different_line)
    If streams are the same, return none
    """
    
    def compareLines(compared, model):
        length = min(len(model), len(compared))
        for i in range(0, length):
            if compared[i] != model[i]:
                return i            
        return None
    
    identical = False
    line = 1       
    while(True):
        comparedLine = compared.readline().split()
        modelLine = model.readline().split()
        if not comparedLine and not modelLine:
            identical = True
            break

        cmpResult = compareLines(comparedLine, modelLine)
        if cmpResult != None:
            message = "Line %s: read %s expected %s" % (line, comparedLine[cmpResult].decode(), modelLine[cmpResult].decode()) 
            break        
        if len(comparedLine) < len(modelLine):
            message = "Line %s: end of line, expected %s" % (line, modelLine[len(comparedLine)].decode())
            break
        elif len(comparedLine) > len(modelLine):
            message = "Line %s: rubbish at the end of line." % line
            break           
        
        line += 1
               
    if identical:
        return None
    else:
        return (message, line)

def _resultCheck(inStream, outStream, modelOutStream):
    return compareFiles(outStream, modelOutStream)

def _advencedResultCheck(inStream, outStream, modelOutStream):
    return advencedCompareFiles(outStream, modelOutStream)[0]

resultCheck = _resultCheck
advencedResultCheck = _advencedResultCheck

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

def getFilesFromFolder(folder, extensions=None, subdirectories=False):
    """
    Returns list of files from given folder which have
    given extension or extensions. Default returns list of all files.
    """
    if isinstance(extensions, str): extensions = (extensions,)
    
    filesList = list()
    if subdirectories:
        for path, _, files in os.walk(folder):
            for name in files:
                filesList.append( os.path.join(path, name) )
    else:
        filesList = [os.path.join(folder,f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder,f)) ]
    
    if extensions is not None:
        filesList = [ f for f in filesList if getFileNameExtension(f) in extensions ]  
    
    return filesList

class AsynchronousStreamRelay(threading.Thread):
    def __init__(self, fromStream, toStream, closeStreamAfterDone = True):
        assert callable(fromStream.read)
        assert callable(toStream.write)
        threading.Thread.__init__(self)
        self.fromStream = fromStream
        self.toStream = toStream        
        self.chunkSize = 1024
        self.closeStreamAfterDone = closeStreamAfterDone
        
    def run(self):
        try:
            chunk = self.readChunk()
            while chunk:
                self.toStream.write(chunk)
                chunk = self.readChunk()
                
            if self.closeStreamAfterDone:   
                self.toStream.close()
        except IOError:
            pass
            
        
    def readChunk(self):
        return self.fromStream.read(self.chunkSize)

def callProcess(commandLine, inputStream, outputStream, timeLimit = float("inf")):     
    def timeLimiter(process):
        pollSeconds = 0.001
        startTime = time.time()
        deadline = startTime + timeLimit    
        while time.time() < deadline and process.poll() == None:
            time.sleep(pollSeconds)
        processTime = time.time() - startTime
        if process.poll() == None:
            process.terminate()        
        process.wait()        
        return processTime
  
    if(isinstance(commandLine, str)):
        commandLine = (commandLine,)
        
    if(getFileNameExtension(commandLine[0]) == 'py'):
        commandLine = (sys.executable,) + commandLine

    popenArgs = {'args' : commandLine, 'stdin': subprocess.PIPE, 'stdout': subprocess.PIPE}    
    process = subprocess.Popen(**popenArgs)
        
    stdin_writer = AsynchronousStreamRelay(inputStream, process.stdin)
    stdin_writer.start()
    stdout_reader = AsynchronousStreamRelay(process.stdout, outputStream, False)
    stdout_reader.start()

    processTime = timeLimiter(process)
   
    stdin_writer.join()    
    stdout_reader.join()    
    process.stdout.close()   
   
    return (process.poll(),processTime)

def createFolder(folderName):
    """Creates folder. If folder exists, does nothin."""
    if not os.path.exists(folderName):
        os.makedirs(folderName)

def waitForKey():
    input("Press Enter to continue...")    

def assertFileExist(filename):
    if  not os.path.isfile(filename):
        print("File not found %s" % os.path.basename(filename) )
        waitForKey()
        exit()

def assertFolderExist(foldername):
    if  not os.path.isdir(foldername):
        print("Folder not found %s" % os.path.basename(foldername) )
        waitForKey()
        exit()

def saveToFile(string, filename):
    try:
        fileHandle = open(filename, "wb")
        fileHandle.write(string)
    except IOError:
        print("Error when writing to file %s" % filename)
    finally:
        fileHandle.close()

def tryDeleteFile(filename):
    try:
        os.remove(filename)
        return True
    except OSError:
        return False

def splitTestName(testname):
    """
    Divide testname in touple (name, number, text after number).
    If pattern can't be matched, tre touple (testname, "","") is returned.
    testname must be string
    """
    if not hasattr(splitTestName, "pattern"):
        splitTestName.pattern = re.compile("^([a-zA-Z_]+)(\d+)([a-zA-Z]*)")
        
    found = splitTestName.pattern.search(testname)
    if found == None:
        return (testname, 0, "")
    else:
        result = found.groups();
        return (result[0], int(result[1]), result[2])

class Test():
    @property
    def haveModelOut(self):
        raise NotImplementedError()
       
    @property
    def inStream(self):
        return io.BytesIO(self.inData)
    
    @property
    def modelOutStream(self):
        return io.BytesIO(self.modelOutData)
    
    @property
    def inData(self):
        if not hasattr(self, "_inData"):
            self._genInData()
        return self._inData
    
    @property
    def modelOutData(self):   
        if not self.haveModelOut:
            raise Exception("Test don't have model out!")
            
        if not hasattr(self, "_modelOutData"):
            self._genModelOutData()
        return self._modelOutData     
    
    def _genModelOutData(self):
        raise NotImplementedError()
    
    def _genInData(self):
        raise NotImplementedError()
    
    def saveInData(self, folder = "."):
        assertFolderExist(folder)
        filename = "%s.in" % self.testName
        saveToFile(self.inData, os.path.join(folder, filename))
        
    def saveModelOutData(self, folder = "."):
        assertFolderExist(folder)
        filename = "%s.out" % self.testName
        saveToFile(self.modelOutData, os.path.join(folder, filename))
    

class TestProvider():
    def getTests(self):
        raise NotImplementedError()
    
    def sortTests(self, testList):
        assert isinstance(testList, list)
        splitTestPath = lambda testName: splitTestName(os.path.basename(testName))        
        testList.sort(key = lambda testName: splitTestPath(testName))
        testList.sort(key = lambda testName: not splitTestPath(testName)[2] == "ocen")
 
    def onlyWithExtension(self, testList, extension):
        assert isinstance(extension, str)
        assert isinstance(testList, list)
        return [ filename for filename in testList if getFileNameExtension( os.path.basename(filename)  ) == extension ]
    
    def getOutFilePath(self, inFilePath):
        modelOutFilePath = re.sub(r'\.in$', r'.out', inFilePath, flags=re.IGNORECASE)
        modelOutFilePath = re.sub(r'^in(?=[/\\])', r'out', modelOutFilePath)
        modelOutFilePath = re.sub(r'([/\\])in(?=[/\\])', r'\1out', modelOutFilePath) 
        return modelOutFilePath
        
 
class TestFromFolder(Test):
    def __init__(self, inFilename, modelOutFilename):
        self.inFilename = inFilename
        self.modelOutFilename = modelOutFilename
        testBaseName = os.path.basename(inFilename)
        self.testName = os.path.splitext(testBaseName)[0]
    
    @property
    def haveModelOut(self):
        return self.modelOutFilename != None
    
    def _genInData(self):
        inFile = open(self.inFilename, 'rb')
        self._inData = inFile.read()
        inFile.close()        
    
    def _genModelOutData(self):       
        modelOutFile = open(self.modelOutFilename, 'rb')
        self._modelOutData = modelOutFile.read()
        modelOutFile.close()
  

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
    def __init__(self, generatorPath, testNumber, testName = None, modelSolutionPath = None, nameSuffix = ""):
        assertFileExist(generatorPath)
        if modelSolutionPath != None:
            assertFileExist(modelSolutionPath)
        
        if testName != None:
            self.testName = testName
        else:
            self.testName = "random"
        
        self.testNumber = testNumber
        self.testName = "%s%s%s" % (self.testName, self.testNumber, nameSuffix)
        self.generatorPath = generatorPath   
        self.modelSolutionPath = modelSolutionPath    
              
    @property
    def haveModelOut(self):
        return self.modelSolutionPath != None
    
    def _genInData(self):        
        inStream = io.BytesIO()
        generatorArgsStream = io.BytesIO( str(self.testNumber).encode() )
        code, _ = callProcess(self.generatorPath, generatorArgsStream, inStream)
        
        if code != 0:
            print("\nCritical Error. In generator crash. Exiting.")
            exit()
            
        self._inData = inStream.getvalue()
        if len(self._inData) == 0:
            print("\nCritical Error. In generator wrote no output. Exiting.")
            exit()
            
    def _genModelOutData(self):      
        modelOutStream = io.BytesIO()
        code, _ = callProcess(self.modelSolutionPath, self.inStream, modelOutStream)
        
        if code != 0:
            print("\nCritical Error. Model solution crash. Exiting.")
            exit()
        
        self._modelOutData = modelOutStream.getvalue()
        if len(self._modelOutData) == 0:
            print("\nCritical Error. Model wrote no output. Exiting.")
            exit()
    
    
class RandomTestProvider(TestProvider):
    def __init__(self, testGenerator, testName, modelSolutionPath = None, nameSuffix = "", testLimit = None):
        assertFileExist(testGenerator)
        if modelSolutionPath != None:
            assertFileExist(modelSolutionPath)
        self.testGenerator = testGenerator
        self.testName = testName
        self.modelSolutionPath = modelSolutionPath
        self.nameSuffix = nameSuffix
        self.testLimit = testLimit
    
    def getTests(self):
        index = 0
        while(True):
            index = index + 1
            yield RandomTest(self.testGenerator, index, self.testName, self.modelSolutionPath, self.nameSuffix)            
            if self.testLimit is not None and self.testLimit <= index:
                break 
 
class TestFromZip(Test):
    def __init__(self, zipFile, inFilename, modelOutFilename):
        self.zipFile = zipFile
        self.inFilename = inFilename
        self.modelOutFilename = modelOutFilename
        testBaseName = os.path.basename(inFilename)
        self.testName = os.path.splitext(testBaseName)[0]
    
    @property  
    def haveModelOut(self):
        return self.modelOutFilename != None
    
    def _genInData(self):
        fileInData = self.zipFile.open(self.inFilename, 'r')
        self._inData = fileInData.read()
        fileInData.close()
        
    def _genModelOutData(self):       
        fileModelOutData = self.zipFile.open(self.modelOutFilename, 'r')
        self._modelOutData = fileModelOutData.read()
        fileModelOutData.close()
               
class TestFromZipProvider(TestProvider):
    def __init__(self, filename):
        assertFileExist(filename)
        self.zipFile = zipfile.ZipFile(filename)
        if not self.zipFile.testzip() == None:
            raise zipfile.BadZipfile()
        
        namelist = self.zipFile.namelist()
           
        self.fileInList = self.onlyWithExtension(namelist, "in")
        self.fileOutList = self.onlyWithExtension(namelist, "out")                
        self.fileOutList = set(self.fileOutList)
        self.sortTests(self.fileInList)        
        
    def getTests(self):
        for filename in self.fileInList:  
            modelOutFile = self.getOutFilePath(filename)
                        
            if not modelOutFile in self.fileOutList:
                modelOutFile = None
                
            yield TestFromZip(self.zipFile, filename, modelOutFile)   

class RunResult():
    def __init__(self):
        self.returnCode = None
        self.processTime = None
        self.result = None
        self.outData = None
        
    @property
    def outStream(self):
        return io.BytesIO(self.outData)
    

class BasicRunner():
    def __init__(self, programName):
        assertFileExist(programName)            
        self.programName = programName
        self.timeLimit = 10
        self.ignoreOutput = False
    
    def run(self, test):
        return self.doRun(self.programName, test)
    
    def doRun(self, command, test):
        runResult = RunResult()
        outStream = io.BytesIO()     
        runResult.returnCode, runResult.processTime = callProcess(command, 
                                                                 test.inStream, 
                                                                 outStream, 
                                                                 self.timeLimit
                                                                 )
        runResult.outData = outStream.getvalue()
        
        runResult.result = "OK"
        if runResult.processTime >= self.timeLimit:
            runResult.result = "TLE"
        elif runResult.returnCode != 0:
            runResult.result = "RE"
        elif self.ignoreOutput:
            runResult.result = "IGNORE"
        elif len(runResult.outData) == 0:
            runResult.result = "NF"
        elif not test.haveModelOut:
            runResult.result = "NOMODEL"        
        elif not resultCheck(test.inStream, runResult.outStream, test.modelOutStream):
            runResult.result = "WA"                  
                    
        return runResult
    
     
class OITimeToolRunner(BasicRunner):
    def __init__(self, programName, oitimetoolPath = ""):
        assertFileExist(programName)
        self.programName = programName
        
        self.oitimetoolDllPath = "oitimetool\oitimetool.dll"
        self.pinPath = "oitimetool\pin\pin.exe"
        self.oitimetoolDllPath = os.path.join(oitimetoolPath, self.oitimetoolDllPath)
        self.pinPath = os.path.join(oitimetoolPath, self.pinPath)
        
        self.oitimetoolCommand = (self.pinPath, "-t", self.oitimetoolDllPath, "--", self.programName)
        self.timeLimit = 30
        self.ignoreOutput = False
        self.haveErrors = False
        
        assertFileExist(self.oitimetoolDllPath)
        assertFileExist(self.pinPath)
        
    def run(self, test):
        return self.doRun(self.oitimetoolCommand, test)


class TestCounter():
    def __init__(self):
        self.queue = collections.deque()
    
    def rate(self):
        timeRange = (time.time() - self.queue[0])
        if timeRange == 0:
            return 0
        else:
            return len(self.queue) / timeRange
    
    def testDone(self):
        self.queue.append( time.time() )
        while len(self.queue) >= 10:
            self.queue.popleft()


import argparse

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
        
    if args.generator != None:
        assertFileExist(args.generator[0])
        assertFileExist(args.generator[1])
        generatorPath = args.generator[0]
        modelPath = args.generator[1]
        testName = os.path.splitext(args.program)[0]
        value = (RandomTestProvider, (generatorPath, testName, modelPath) ) 
        testProviderList.append(value)
        
    return testProviderList

def getRunnerFromArgs(args, parser):
    runner = None
    if args.oitimetool != None:
        if args.oitimetool == True:
            runner = OITimeToolRunner(args.program)  
        else:
            runner = OITimeToolRunner(args.program, args.oitimetool)  
    else:
        runner = BasicRunner(args.program)
    
    runner.ignoreOutput = args.ignore_out
    if args.time_limit != None:
        runner.timeLimit = args.time_limit
        
    return runner

def testingLoop(testProviderList, runner, args):    
    number_of_fails = 0
    number_of_tests = 0
    for testProviderArgs in testProviderList:    
        TestProviderClass = testProviderArgs[0]
        testProviderArgs = testProviderArgs[1]
        print("Procesing tests from \"%s\"" % (testProviderArgs,) )
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
    
            print(runResult.result)
            
            number_of_tests += 1
            if runResult.result not in ("OK", "IGNORE"):
                number_of_fails += 1
                print(advencedResultCheck(test.inStream, runResult.outStream, test.modelOutStream))
                
                if args.wrong_folder != None:
                    createFolder(args.wrong_folder)
                    test.saveInData(folder = args.wrong_folder)
                    test.saveModelOutData(folder = args.wrong_folder)
                    
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
    parser.add_argument('--oitimetool', '-o', help='use oitimetool, optionally path to oitimetool folder', nargs='?', const=True)
    parser.add_argument('--keyword', '-k', help='run only tests with specified keyword in name')
    parser.add_argument('--break_after', '-b', help='break testing after N fails', type=int, metavar='N' )
    parser.add_argument('--tests_limit', '-n', help='run only N first tests', type=int, metavar='N' )
    
    args = parser.parse_args()    
    assertFileExist(args.program)
    testProviderList = getProviderListFromArgs(args, parser)
    runner = getRunnerFromArgs(args, parser)
    
    if args.checker is not None:
        try:
            if getFileNameExtension(args.checker) == 'py':
                args.checker = os.path.splitext(args.checker)[0]
            
            import importlib
            checker = importlib.import_module(args.checker)
            
            if not hasattr(checker, 'check'):
                print("Module %s don't have check function!" % args.checker)
                exit()
                
            #print("Nadpisalem funkcje sprawdzajace.")
            global resultCheck
            global advencedResultCheck
            resultCheck = lambda inS, outS, modelS: checker.check(inS, outS, modelS) == "OK"
            advencedResultCheck = lambda inS, outS, modelS: checker.check(inS, outS, modelS)
            
        except ImportError:
            print("Could not import %s!" % args.checker)
            exit()

    
    testingLoop(testProviderList, runner, args)    
       
       
#import cProfile
        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt - Exiting...")
        

