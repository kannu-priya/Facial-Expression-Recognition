import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import random
import numpy.linalg as LA
#from sklearn.metrics import confusion_matrix
#from imblearn.over_sampling import RandomOverSampler, SMOTE
from collections import Counter
from PIL import Image
import os

# Take a 2304 long vector and plot it as a 48x48 image
def vectortoimg(v,show=True):
    vLen = len(v)
    vSide = np.sqrt(vLen).astype(int)
    plt.imshow(v.reshape(vSide, vSide),interpolation='None', cmap='gray')
    plt.axis('off')
    if show:
        plt.show()

# Arguments: X is training feature vectors
#            T is training class labels (not needed other than for scatter plot)
# Returns:   Mean vector of X
#            Eigen vectors, as rows, with max on top
#            Principal components of X
def performPCA(X, T, showScatterPlot=False, showSeparatePlots=False):
    # PERFORM the XZCVP process
    # X -> Z
    muX = np.mean(X, axis=0) # get means of columns, by setting axis=0
    Z = X - muX
    
    # Z -> C
    C = np.cov(Z.T) # alter input such that each row is a feature
    
    # C -> V
    [eigVal, V] = LA.eigh(C)
    
    eigVal = np.flipud(eigVal) # get largest value to beginning
    V = np.flipud(V.T)         # get eigen vectors to be rows, with largest one first
    row = V[0,:] #Check once again
    np.dot(C,row) - (eigVal[0]*row) #If the matrix product C.row is the same as λ[0]*row, this should evaluate to [0,0,0]
    
    # V -> P
    P = np.dot(Z, V.T) # Nxd DOT dxd = Nxd

    # Draw SCATTER PLOT
    if (showScatterPlot):
        reducedP = P[:, 0:2]
        fig = plt.figure()
        ax = fig.add_subplot(111, facecolor='black')
        
        for digit in np.unique(T):
            ix = np.where(T == digit)
            ax.scatter(reducedP[ix,0], reducedP[ix,1], s=5, c=mapOfColors[digit], label='Class: '+mapOfEmotion[digit], linewidths=0, marker="o")
        ax.set_aspect('equal')
        plt.legend(markerscale=5.0)
        plt.show()

    # Draw SCATTER PLOT (separate for each class)
    if (showSeparatePlots):
        plt.close('all')
        fig = plt.figure()
        
        reducedP = P[:, 0:2]
        
        for digit in np.unique(T):
            ix = np.where(T == digit)
            ax = fig.add_subplot(plotLoc[digit], facecolor='black')
            ax.scatter(reducedP[ix,0], reducedP[ix,1], s=5, c=mapOfColors[digit], label='Class: '+mapOfEmotion[digit], linewidths=0, marker="o")
            ax.set_title(mapOfEmotion[digit])
            ax.set_xbound(-6000, 6000)
            ax.set_ybound(-3500, 3500)
        ax.set_aspect('equal')
        #plt.legend(markerscale=5.0)
        plt.show()

    return muX, V, P
    
# For a vector 'x', returns the pdf, in the form of log(pdf)
#   Optimized as it takes 'inverse of cov. matrix' and 
#   'log of det. of cov. matrix', and as such, does not 
#   have to recompute them 
def pdfLogOpt(x, mu, cvMtxInv, logDet):
    diffFromMean = (x - mu)
    powOfE = diffFromMean.dot(cvMtxInv)
    powOfE = powOfE.dot(diffFromMean.T)
    numerPowOfE = -.5 * powOfE

    denomPowOfE = np.log(2*np.pi) + logDet*0.5

    return (numerPowOfE-denomPowOfE)

# Build a bayesian classifier, given the training data (X)
#   and the training labels (T). It will return 
#   1. the training data split up by classes
#   2. counts for each class
#   3. mean vector for each class
#   4. cov. matrix for each class
def buildBayesianClassifier(X, T):
    # split training data into class-specific sets
    XByClass = []
    nByClass = []
    muByClass = []
    cvMtxByClass = []
    
    for cLabel in np.unique(T):
        ix = np.where(T == cLabel)
        ix = ix[0] # as ix is initially a tuple with one element
        XForAClass = X[ix,:]
        XByClass.append(XForAClass)
    
        # get SAMPLE SIZE
        nByClass.append(len(XForAClass))

        # get MEAN VECTOR
        mu = np.mean(XForAClass, axis=0)
        mu = mu.reshape(1, mu.shape[0])
        muByClass.append(mu)
    
        # get CovarianceMatrix
        cvMtx = np.cov(XForAClass.T) # transpose so that each column is a single obsv.
        cvMtxByClass.append(cvMtx)

    return XByClass, nByClass, muByClass, cvMtxByClass

# Make predictions on given 'queries', using a supplied bayesian model 
#   which is specified in terms of (count, mean vector, cov. matrix) for 
#   each class, and also the 'label' for each class.
#   Currently, returns the predicted class label for each query
def predictWithBayesian(nByClass, muByClass, cvMtxByClass, classLabels, queries):
    # for each QUERY, compute bayesian numbers and produce prob
    predLabel = []
    predProb = np.zeros(len(queries))

    cvMtxInvByClass = np.linalg.inv(cvMtxByClass)
    sByClass, logDetByClass = np.linalg.slogdet(cvMtxByClass)
    
    if (0 in sByClass):
        print('Determinant of these cvMtx is 0! ', np.where(sByClass==0)[0])
    elif (-1 in sByClass):
        print('Determinant of these cvMtx is negative! ', np.where(sByClass==-1)[0])
    else:
        for iQuery, xQueryVal in enumerate(queries):
            estLogByClass = [0.]*len(classLabels)
            for iClass, labelVal in enumerate(classLabels):
                estLogByClass[iClass] = pdfLogOpt(xQueryVal, muByClass[iClass], cvMtxInvByClass[iClass], logDetByClass[iClass]) + np.log(nByClass[iClass])

            likelyClass = np.argmax(estLogByClass)
            predLabel.append(classLabels[likelyClass])

            #if (np.remainder(iQuery,1000) == 0):
                #print('Done with query# ', iQuery)

    return predLabel, predProb

# Given a feature's value, the feature's range, and total number of bins, 
# identify the bin to which that particular value belongs
def binForValue(xValue, B, xmin, xmax):
    computedBin = np.round((B-1)*(xValue-xmin)/(xmax-xmin)).astype('int32')
    return np.clip(computedBin, 0, (B-1))

# Build a sparse histogram (instead of n-dim array, use a dictionary that only 
# stores populated bins)
def buildHistogramClassifier(X, T, B, verbose=False):
    hist = {} # an empty dictionary, key is set of indices, value is count for each class at that position
    
    nSamples = X.shape[0]
    nFeatures = X.shape[1]
    nDistinctClasses = len(np.unique(T))
    minVals = np.amin(X, axis=0) # find mins for each column
    maxVals = np.amax(X, axis=0)
    
    binIndices = np.zeros((nSamples, nFeatures), dtype=np.uint8)
    for iFeature in np.arange(nFeatures):
        binIndices[:,iFeature] = binForValue(X[:,iFeature], B, minVals[iFeature], maxVals[iFeature])

    for i, binIndexSet in enumerate(binIndices):
        # binIndexSet is the key into the dict
        # if it already exists, get the value
        # else create a new value (vector of length nClass)
        # based on G[i], increment corresponding position in vector
        tupleOfIndices = tuple(binIndexSet)
        classIndex = T[i] # since labels are 0-based numbers
        if tupleOfIndices not in hist.keys():
            hist[tupleOfIndices] = np.zeros((nDistinctClasses), dtype=np.uint16)
        hist[tupleOfIndices][classIndex] += 1
        
        if (verbose):
            if (hist[tupleOfIndices][classIndex] > 8000):
                print('Nearing the limit for ', classIndex)
            if (np.remainder(i, 1000) == 0):
                print('Done with sample# ', i)

    return hist, minVals, maxVals

# Based on QUERIES, grab numbers from histograms and determine most likely class
def predictWithHistogram(H, B, minVals, maxVals, nDistinctClasses, queries):
    predLabel = []
    predProb = np.zeros(len(queries))
    
    nQueries = queries.shape[0]
    nFeatures = queries.shape[1]
        
    binIndices = np.zeros((nQueries, nFeatures), dtype=np.uint8)
    for iFeature in np.arange(nFeatures):
        binIndices[:,iFeature] = binForValue(queries[:,iFeature], B, minVals[iFeature], maxVals[iFeature])

    for i, binIndexSet in enumerate(binIndices):
        # binIndexSet is the key into the dict
        # if it already exists, get the value
        # else create a new value (vector of length nClass)
        # based on G[i], increment corresponding position in vector
        tupleOfIndices = tuple(binIndexSet)
        
        if tupleOfIndices in H.keys():
            countForClasses = H[tupleOfIndices]
            likelyClass = np.argmax(countForClasses)
        else:
            likelyClass = -1
        predLabel.append(likelyClass)
        
    return predLabel, predProb


### Classes: 0=Angry, 1=Disgust, 2=Fear, 3=Happy, 4=Sad, 5=Surprise, 6=Neutral
mapOfEmotion = {0:"Angry", 1:"Disgust", 2:"Fear", 3:"Happy", 4:"Sad", 5:"Surprise", 6:"Neutral"}
mapOfColors = {0: [1,0,0,0.5], 1: [0,1,0,0.5], 2: [0,0,1,0.5], 3:[1,1,0,0.5], 4:[0,1,1,0.5], 5:[1,0,1,0.5], 6:[0.5,0.5,0.5,0.5]}
plotLoc = {0: 241, 1: 242, 2: 243, 3:244, 4:245, 5:246, 6:247}

balanceTheTrainingSet = False
augmentRotatedImages = False
trainOnOriginalComponents = False
showSingleScatter = False
showSeparateScatter = False
tryHistogramClassifier = False
performValidation = True
determineAccuracyVariation = False
predictOnPublicTestSet = False
predictOnTrainingSet = False
predictOnNewDataJPEG = False
predictOnNewDataCSV = True

## Data Loading and Splitting
dataFolderPath = "D:\\python_ML\\Project\\"
data=pd.read_csv(dataFolderPath + "FaceRecognition.csv")

data=data.drop(columns='Unnamed: 0')

Train_data=data[data['X2306']=='Training'].drop(columns='X2306')
Test_data=data[data['X2306']=='PrivateTest'].drop(columns='X2306')
Train_labels=Train_data.iloc[:,0].values
Test_labels=Test_data.iloc[:,0].values
Train_data=Train_data.drop(columns='X1').values
Test_data=Test_data.drop(columns='X1').values

# downsample from 64bit int to an 8bit uint
Train_data = Train_data.astype(dtype=np.uint8)
Train_labels = Train_labels.astype(dtype=np.uint8)
Test_data = Test_data.astype(dtype=np.uint8)

if (balanceTheTrainingSet):
    ros = RandomOverSampler(random_state=0)
    Train_data, Train_labels = ros.fit_resample(Train_data, Train_labels)
    #Train_data, Train_labels = SMOTE().fit_resample(Train_data, Train_labels)
    print(sorted(Counter(Train_labels).items()))

# OPTIONAL, AUGMENT the TRAINING data with ROTATIONS
if (augmentRotatedImages):
    otherDataFiles = []
    #otherDataFiles = ["fer2013_3toleft.csv", "fer2013_3toright.csv", "fer2013_6toleft.csv", "fer2013_6toright.csv"]
    #otherDataFiles = ["fer2013_3toleft.csv", "fer2013_3toright.csv", "fer2013_6toleft.csv", "fer2013_6toright.csv", "fer2013_10toleft.csv", "fer2013_10toright.csv"]
    
    nTrgVectors = Train_data.shape[0] 
    for otherDataFile in otherDataFiles:
        data = pd.read_csv(dataFolderPath + otherDataFile)
        data = data.values.astype(dtype=np.uint8)
        
        newLabels = data[:,0]
        newData = data[:,1:]
    
        # 'data' is missing the first training image
        Train_data = np.vstack( (Train_data, newData[0:nTrgVectors]) ) 
        Train_labels = np.hstack( (Train_labels, newLabels[0:nTrgVectors]) )
    
# OPTIONAL try on regular data (i.e., original components)
if (trainOnOriginalComponents):
    TrainByClass, nByClass, muByClass, cvMtxByClass = buildBayesianClassifier(Train_data, Train_labels)
    
    # now, predict on the PRIVATE test set with Bayesian classifier
    Test_data = Test_data.astype(dtype=np.uint8)
    predLabelTest, predProbTest = predictWithBayesian(nByClass, muByClass, cvMtxByClass, np.unique(Train_labels), Test_data)
    res = (predLabelTest==Test_labels)
    print('Accuracy over PRIVATE TEST SET is ', res.sum()/len(Test_labels))
    
    # also, predict on the TRAINING set with Bayesian classifier
    predLabelTrg, predProbTrg = predictWithBayesian(nByClass, muByClass, cvMtxByClass, np.unique(Train_labels), Train_data)
    res = (predLabelTrg==Train_labels)
    print('Accuracy over TRAINING SET is ', res.sum()/len(Train_labels))

# Peform PCA on the training data
muTrain, V, PTrain = performPCA(Train_data, Train_labels, showSingleScatter, showSeparateScatter)

# 2 gives us accuracy of 25.57%
# 19 gives us accuracy of 32.79%
# 50 gives us accuracy of 38.31%
# 100 (after switching to log scale in pdf calc) gives 39.87%
# 125 -> 40.51%
# 150 (only predicting label) gives 41.60%
# 200 gives 42.24%
# 250 gives 43.02%
# 275 -> 43.44%
# 300 gives 43.32%
# 325 -> 44.11%
# 350 gives 43.80%, 355->44.16%, 358->44.13%, 359->44.08%
# 360 gives 44.25%, 361->44.22%, 362->44.25%, 363->44.08%, 365->43.94%
# 375, 380 gives 44.16%
# 385 fails!
# 390 gives 20.84% ?
# 400 gives 23.54%
# 500 gives 23.01%

nOrigDim = Train_data.shape[1]
imgWidth = np.sqrt(nOrigDim).astype(int)
nPCDim = 360
reducedV = V[0:nPCDim, :]

# try recovering some of the images, to see how they look
reducedP = PTrain[:, 0:nPCDim]
xRec = np.dot(reducedP, reducedV) + muTrain

# randomly pick and view few images and their label
print("Checking multiple training images by plotting them.\nBe patient:")
plt.close('all')
fig = plt.figure()
nrows=8
ncols=4
for row in range(nrows):
    for col in range(ncols):
        ax = plt.subplot(nrows, ncols*2, row*ncols*2 + 2*col + 1)
        
        nImgToDraw = random.randint(0, Train_data.shape[0]-1)
        vectortoimg(Train_data[nImgToDraw], show=False)
        ax.set_title(mapOfEmotion[Train_labels[nImgToDraw]])
        
        ax = plt.subplot(nrows, ncols*2, row*ncols*2 + 2*col + 2)
        vectortoimg(xRec[nImgToDraw], show=False)
plt.show()

if (tryHistogramClassifier):
    # 32,4 -> 0.1582613541376428 
    # 8,14 -> 0.12120367790470883
    accMtx = np.zeros((30,15), dtype=float)
    ZTest = Test_data - muTrain

    for nBin in np.arange(2,26,1):
        for nPC in np.arange(2,12,1):
            H, minVals, maxVals = buildHistogramClassifier(PTrain[:,0:nPC], Train_labels, nBin)

            PTest = np.dot(ZTest, V[0:nPC,:].T)
            predLabelTest, predProbTest = predictWithHistogram(H, nBin, minVals, maxVals, len(np.unique(Train_labels)), PTest)

            testResCM = confusion_matrix(Test_labels, predLabelTest)
            #print('Confusion matrix is:\n', testResCM)
            acc = testResCM.diagonal().sum() / testResCM.sum()
            print('Accuracy for ', nBin, '-', nPC, ' is ', acc)
            accMtx[nBin][nPC] = round(acc*100,2)

# now, get a Bayesian classifier for the training data and labels
TrainByClass, nByClass, muByClass, cvMtxByClass = buildBayesianClassifier(reducedP, Train_labels)

# now, predict on the PRIVATE test set with Bayesian classifier
# convert test set into queries (in the form of PCs)
ZTest = Test_data - muTrain
PTest = np.dot(ZTest, reducedV.T)

predLabelTest, predProbTest = predictWithBayesian(nByClass, muByClass, cvMtxByClass, np.unique(Train_labels), PTest)

# testResCM = confusion_matrix(Test_labels, predLabelTest)
# print('Confusion matrix is:\n', testResCM)
# acc = testResCM.diagonal().sum() / testResCM.sum()
# print('Accuracy over PRIVATE TEST SET is ', acc)
# print('PPV values for the classes are:', testResCM.diagonal() / testResCM.sum(axis=0))
# print('Sensitivity values for the classes are:', testResCM.diagonal() / testResCM.sum(axis=1))
acc = (Test_labels==predLabelTest).sum()/len(Test_labels)
print('Accuracy over PRIVATE TEST SET is ', acc)

# OPTIONAL, perform 80/20 splits and see if we can pick a better classifier!
if (performValidation):
    valP = reducedP[:,:300] # only include the first 120 PCs
        # crashes freq. with 360 PCs, as it appears that the 
        # CovMtx for class#1, which has less samples, has a negative determinant!

    # TBD: keep track of the best model!!
    for attempt in np.arange(0, 10, 1):
        rndInd = np.random.permutation(reducedP.shape[0])
        nTrgSize = int(0.8*reducedP.shape[0])
        trgInd, testInd = rndInd[:nTrgSize], rndInd[nTrgSize:]

        # randomly split training data 80/20
        # use 80 for training, and test on 20
        rndTrgData, rndTestData = valP[trgInd], valP[testInd]
        rndTrgLabels, rndTestLabels = Train_labels[trgInd], Train_labels[testInd]

        # now, get a Bayesian classifier for the training data and labels
        TrainByClass, nByClass, muByClass, cvMtxByClass = buildBayesianClassifier(rndTrgData, rndTrgLabels)

        predLabelTest, predProbTest = predictWithBayesian(nByClass, muByClass, cvMtxByClass, np.unique(Train_labels), rndTestData)
        if (len(predLabelTest) == len(rndTestLabels)):
            acc = (rndTestLabels==predLabelTest).sum()/len(rndTestLabels)
            print('Accuracy over PRIVATE TEST SET is ', acc)

# OPTIONAL, determine accuracy as number of PCs changes
if (determineAccuracyVariation):
    nPCList, cmList, accList, ppvList, sensList = [], [], [], [], []
    for nPCDim in np.arange(2, nOrigDim, 23):
        reducedV = V[0:nPCDim, :]
        reducedP = PTrain[:, 0:nPCDim]
    
        # now, get a Bayesian classifier for the training data and labels
        TrainByClass, nByClass, muByClass, cvMtxByClass = buildBayesianClassifier(reducedP, Train_labels)
        
        # now, predict on the PRIVATE test set with Bayesian classifier
        # convert test set into queries (in the form of PCs)
        #ZTest = Test_data - muTrain
        PTest = np.dot(ZTest, reducedV.T)
        
        predLabelTest, predProbTest = predictWithBayesian(nByClass, muByClass, cvMtxByClass, np.unique(Train_labels), PTest)
        
        nPCList.append(nPCDim)
        # check if we were able to predict successfully (as at higher dimensions
        # the cov. matx gets unstable and we get no predictions back)
        if (len(predLabelTest) == len(Test_labels)):
            # testResCM = confusion_matrix(Test_labels, predLabelTest)
            # #print('Confusion matrix is:\n', testResCM)
            # cmList.append(testResCM)
            # acc = testResCM.diagonal().sum() / testResCM.sum()
            acc = (Test_labels==predLabelTest).sum()/len(Test_labels)
            print('Accuracy for ', nPCDim, ' is ', acc)
            accList.append(acc)
            #print('PPV values for the classes are:', testResCM.diagonal() / testResCM.sum(axis=0))
            #ppvList.append(testResCM.diagonal() / testResCM.sum(axis=0))
            #print('Sensitivity values for the classes are:', testResCM.diagonal() / testResCM.sum(axis=1))
            #sensList.append(testResCM.diagonal() / testResCM.sum(axis=1))
        else:
            accList.append(0.0)
        
        accArr = (np.array(accList) * 100.).round(2)
        plt.plot(nPCList, accArr, 'go-', linewidth=1, markersize=5)
        plt.xlabel('Number of PCs included in training')
        plt.ylabel('Accuracy')
        plt.show()

# OPTIONAL, predict on the PUBLIC test set with Bayesian classifier
if (predictOnPublicTestSet):
    data=pd.read_csv(dataFolderPath + "FaceRecognition.csv")
    data=data.drop(columns='Unnamed: 0')
    Test_data=data[data['X2306']=='PublicTest'].drop(columns='X2306')
    Test_labels=Test_data.iloc[:,0].values
    Test_data=Test_data.drop(columns='X1').values
    Test_data = Test_data.astype(dtype=np.uint8)
    
    ZTest = Test_data - muTrain
    PTest = np.dot(ZTest, reducedV.T)
    
    predLabelTest, predProbTest = predictWithBayesian(nByClass, muByClass, cvMtxByClass, np.unique(Train_labels), PTest)
    res = (predLabelTest==Test_labels)
    print('Accuracy over PUBLIC TEST SET is ', res.sum()/len(Test_labels))

# OPTIONAL, predict on the TRAINING set with Bayesian classifier
# 360 PC dimensions-> 76.61% (with original set of 28709)
# 360 PC dimensions-> 54% (with original+rotated set of 28709*7)
if (predictOnTrainingSet):
    nSamplesToTry = len(reducedP)
    predLabelTrg, predProbTrg = predictWithBayesian(nByClass, muByClass, cvMtxByClass, np.unique(Train_labels), reducedP[0:nSamplesToTry])
    res = (predLabelTrg==Train_labels[0:nSamplesToTry])
    print('Accuracy over TRAINING SET is ', res.sum()/nSamplesToTry)

# OPTIONAL, predict on some random images from team members
imgFolder = r"D:\python_ML\Project\IMAGES_TME"
grayWith3Channels = True # with all 3 channels having same value
if (predictOnNewDataJPEG):
    teamMemberExprFiles = []
    # r=root, d=directories, f = files
    for r, d, f in os.walk(imgFolder):
        for file in f:
            if '.jpg' in file:
                teamMemberExprFiles.append(os.path.join(r, file))

    for exprFile in teamMemberExprFiles:
        pic = Image.open(exprFile)
        pic = pic.resize((imgWidth,imgWidth), resample=Image.LANCZOS)
        imgData = np.array(pic)
        if (len(imgData.shape) == 3) and (imgData.shape[2] >= 3):
            if grayWith3Channels:
                gray = imgData[:,:,0]
            else:
                r, g, b = imgData[:,:,0], imgData[:,:,1], imgData[:,:,2]
                gray = 0.2989 * r + 0.5870 * g + 0.1140 * b
        else:
            gray = imgData
        gray = gray.flatten()
        vectortoimg(gray)
        if (len(gray) == nOrigDim):
            ZTest = gray - muTrain
            PTest = np.dot(ZTest, reducedV.T)
            PTest = PTest.reshape((1, len(PTest)))
            predLabelTest, predProbTest = predictWithBayesian(nByClass, muByClass, cvMtxByClass, np.unique(Train_labels), PTest)
            print(exprFile, ' Predicted Emotion is', mapOfEmotion[predLabelTest[0]])
        else:
            print(exprFile, ' is not the right size!')

if (predictOnNewDataCSV):
    new_data = pd.read_csv(imgFolder + r"\newPictures.csv")
    
    new_labels = new_data.iloc[0:50,0].values # extract the labels, excl 'others'
    new_labels = new_labels.astype(np.uint8)

    new_data = new_data.iloc[0:50,1:2305].values # remove labels from data
    new_data = new_data.astype(dtype=np.uint8)

    ZTest = new_data - muTrain
    PTest = np.dot(ZTest, reducedV.T)
    #PTest = PTest.reshape((1, len(PTest)))
    predLabelTest, predProbTest = predictWithBayesian(nByClass, muByClass, cvMtxByClass, np.unique(Train_labels), PTest)
    print('Accuracy on new images is ', (new_labels==predLabelTest).sum()/len(new_labels))
    #print(exprFile, ' Predicted Emotion is', mapOfEmotion[predLabelTest[0]])
