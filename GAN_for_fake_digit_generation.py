import torch
import torch.nn as nn

import torchvision
from torchvision import datasets
from torchvision import transforms

from torch.autograd import Variable
from torch.utils.data import DataLoader
from torchvision.utils import save_image
from torch import optim
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np
import pickle 
from google.colab import files
from PIL import Image
from zipfile import ZipFile

from sklearn.metrics import confusion_matrix
import itertools

device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
device

from google.colab import drive
drive.mount('/content/gdrive')

path = '/content/drive/MyDrive/Data set'

"""Training data"""

train_data = datasets.MNIST(root= path,
                            train = True,                                   
                            transform=transforms.Compose([
                                       transforms.ToTensor(),
                                       transforms.Normalize((0.5,),(0.5,))
                                   ]),
                            download=True)

"""Hyper Parameters"""

bs = 100 #Batch Size
z_dim = 100 #Z dimensions
D_hidden = 256
G_hidden= 256
image_size = 28*28
lr = 2e-4

train_loader = DataLoader(train_data, batch_size= bs)

"""Discrminator"""

class Discriminator(nn.Module):

  def __init__(self):
    super(Discriminator, self).__init__()
    
    self.main = nn.Sequential(
            # 1st layer
            nn.Linear(image_size, D_hidden*4),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Dropout(0.3),
            # 2nd layer
            nn.Linear(D_hidden * 4, D_hidden * 2),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Dropout(0.3),
            # 3rd layer
            nn.Linear(D_hidden * 2, D_hidden),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Dropout(0.3),
            # output layer
            nn.Linear(D_hidden, 1),
            nn.Sigmoid()
    )    
  def forward(self, x):
      x= x.view(x.size(0),-1)
      return self.main(x)

"""Generator"""

class Generator(nn.Module):
    def __init__(self):
        super(Generator, self).__init__()
        self.main = nn.Sequential(
            # input layer
            nn.Linear(z_dim, G_hidden),
            nn.LeakyReLU(0.2),
            # 1st hidden layer
            nn.Linear(G_hidden, G_hidden * 2),
            nn.LeakyReLU(0.2),
            # 2nd hidden layer
            nn.Linear(G_hidden * 2, G_hidden * 4),
            nn.LeakyReLU(0.2),
            # output layer
            nn.Linear(G_hidden * 4, image_size),
            nn.Tanh()
        )

    def forward(self, x):
        return self.main(x).view(-1, 1, 28, 28)

G = Generator().to(device)
print(G)

D = Discriminator().to(device)
print(D)

"""Optimizers"""

criterion = nn.BCELoss()

D_optimizer = optim.Adam(D.parameters(), lr=lr, betas=(0.5, 0.999))
G_optimizer = optim.Adam(G.parameters(), lr=lr, betas=(0.5, 0.999))

"""**Training**"""

img_list = []
G_losses = []
D_losses = []

num_epoch = 200

D.train()
G.train()

for epoch in range(num_epoch):
  for i,data in enumerate(train_loader,0):
    #train the Discrminator

    real = data[0].to(device)
    b_size= real.size(0)

    real_label = torch.ones(b_size,1).to(device)

    D_optimizer.zero_grad()
    
    real_output = D(real)
    D_loss_real  = criterion(real_output,real_label)
    D_loss_real.backward()
    
    z = Variable(torch.randn(b_size, z_dim).to(device))
    fake = G(z)
    fake_label = torch.zeros(b_size,1).to(device)
    
    fake_output = D(fake)
    D_loss_fake = criterion(fake_output,fake_label)  
    D_loss_fake.backward()
    
    D_loss = D_loss_real + D_loss_fake

    D_optimizer.step()
  
    #train the Generator

    z = Variable(torch.randn(b_size, z_dim).to(device))
    fake = G(z)

    b_size = fake.size(0)
    real_label = torch.ones(b_size,1).to(device)

    G_optimizer.zero_grad()

    output = D(fake)
    G_loss = criterion(output,real_label)

    G_loss.backward()
    G_optimizer.step()

  G_epoch_loss = (G_loss).cpu().detach() 
  D_epoch_loss = (D_loss).cpu().detach()  

  G_losses.append(G_epoch_loss)
  D_losses.append(D_epoch_loss)

  print(f"Epoch {epoch} of {num_epoch}")
  print(f"Generator loss: {G_epoch_loss:.8f}, Discriminator loss: {D_epoch_loss:.8f}")

"""**Final steps**

GAN training accuracy - losses
"""

G_losses = np.array(G_losses)
D_losses = np.array(D_losses)
plt.figure()
plt.plot(G_losses, label='Generator loss')
plt.plot(D_losses, label='Discriminator Loss')
plt.legend()
plt.show()

"""Pickling Generator and Discriminator"""

import pickle
pickle.dump(G, open('G.pkl','wb'))

pickle.dump(D, open('D.pkl','wb'))

files.download('G.pkl')
files.download('D.pkl')

"""**Create new fake data set**"""

sample_size = 100
z = Variable(torch.randn(sample_size, z_dim).to(device))
G.eval()
images = G(z).cpu().detach()

"""Applying function (GAN) one by one and tried to get fake digits"""

images= []
z =[]
for i in range(100):
  Z = Variable(torch.randn(1, z_dim).to(device))
  G.eval()
  img = G(Z).cpu().detach()

  images.append(img)
  z.append(Z)

def view_samples(samples):
    fig, axes = plt.subplots(figsize=(10,10), nrows=10, ncols=10, sharey=True, sharex=True)
    for ax, img in zip(axes.flatten(), samples):
        img = img.detach()
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        im = ax.imshow(img.reshape((28,28)), cmap='Greys_r')

view_samples(images)

"""Save latent samples Z"""

zip_latent = ZipFile('latent.zip','w')
for i in range(100):
  latent = z[i]
  latent = latent.cpu().data.numpy()
  filename= '%003d.txt'%(i+1)
  np.savetxt(filename,[latent],delimiter=',')
  zip_latent.write(filename)
zip_latent.close()

files.download('latent.zip')

"""Save generated fake digits images"""

zip_image = ZipFile('images.zip','w')
for i in range(100):
  img = images[i]
  img = img.reshape((28,28))
  filename= '%003d.png'%(i+1)
  save_image(img,filename)
  zip_image.write(filename)

zip_image.close()
files.download('images.zip')

"""Data preparation for classification"""

train_data=datasets.MNIST(
    root=path,
    train=True,
    transform=transforms.ToTensor(),
    download=True,
)


test_data=datasets.MNIST(
    root=path,
    train=False,
    transform=transforms.ToTensor()
)

from torch.utils.data import DataLoader
loaders = {
    'train' : torch.utils.data.DataLoader(train_data, 
                                          batch_size=100, 
                                          shuffle=True, 
                                          num_workers=1),
    
    'test'  : torch.utils.data.DataLoader(test_data, 
                                          batch_size=100, 
                                          shuffle=True, 
                                          num_workers=1),
}
loaders

"""**Evaluation of created fake dataset**

Classifier
"""

class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()
        self.conv1 = nn.Sequential(         
            nn.Conv2d(
                in_channels=1,              
                out_channels=36,            
                kernel_size=5,              
                stride=1,                   
                padding=2,                  
            ),                              
            nn.ReLU(),                      
            nn.MaxPool2d(kernel_size=2),    
        )
        self.conv2 = nn.Sequential(         
            nn.Conv2d(36, 32, 5, 1, 2),     
            nn.ReLU(),                      
            nn.MaxPool2d(2),                
        )
        # fully connected layer, output 10 classes
        self.out = nn.Linear(32 * 7 * 7, 10)

        
    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        # flatten the output of conv2 to (batch_size, 32 * 7 * 7)
        x = x.view(x.size(0), -1)       
        output = self.out(x)
        return output, x

cnn=CNN()
print(cnn)

cnn_criterion = nn.CrossEntropyLoss()

C_optimizer = optim.Adam(cnn.parameters(), lr=0.01)

"""Training the classifier"""

num_epochs = 25

def train(num_epochs, cnn, loaders):
    
    cnn.train()
        
    total_step = len(loaders['train'])
        
    for epoch in range(num_epochs):
        for i, (images, labels) in enumerate(loaders['train']):
            
            # gives batch data, normalize x when iterate train_loader
            b_x = Variable(images)   # batch x
            b_y = Variable(labels)   # batch y
            output = cnn(b_x)[0]               
            loss = cnn_criterion(output, b_y)
              
            C_optimizer.zero_grad()           
            
            loss.backward()    
                       
            C_optimizer.step()                
            
            if (i+1) % 300 == 0:
                print ('Epoch [{}/{}], Step [{}/{}], Loss: {:.4f}'.format(epoch + 1, num_epochs, i + 1, total_step, loss.item()))
                pass
        pass
    pass

train(num_epochs, cnn, loaders)

import pickle
pickle.dump(cnn, open('C.pkl','wb'))
files.download('C.pkl')

def test():
  cnn.eval()
  with torch.no_grad():
    correct=0
    total=0
    for images, labels in loaders['test']:
      test_output,last_layer=cnn(images)
      pred_y=torch.max(test_output,1)[1].data.squeeze()
      accuracy=(pred_y==labels).sum().item()/float(labels.size(0))
      pass
    print('Test Acc %.2f' % accuracy)
    pass


test()

"""**Evaluation of the created fake data set with real MNIST dataset**

Loading Fake Digits dataset
"""

path = '/content/gdrive/MyDrive/Data set/Fake_Digits/'

fake_digits_dataset = datasets.ImageFolder(path, transform=transforms.Compose([
                                       transforms.ToTensor(),
                                       transforms.Grayscale(num_output_channels=1)])
                                       )

fake_digit_loader = DataLoader(fake_digits_dataset,batch_size = 100,shuffle=True)

fake_digit_loader

"""Accuracy function and confusion matrix to compare the real and fake digits"""

def accuracy(predicted,actual):
  correct = 0
  total = len(predicted)
  for i in range(total):
    if predicted[i] == actual[i]:
      correct += 1
  accuracy = correct / total
  return accuracy

def plot_confusion_matrix(cm, classes, normalize=False, title='Confusion matrix', cmap=plt.cm.Blues):
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)
    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], fmt), horizontalalignment="center", color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')

"""Real MNIST data evaluation with 100 samples as S0 """

S_0 = next(iter(loaders['test']))
imgs_0, lbls_0 = S_0
actual_0 = lbls_0[:100].numpy()

test_output_0,last_layer_0 = cnn(imgs_0[:100])
pred_0 = torch.max(test_output_0,1)[1].data.numpy().squeeze()

print(f'Prediction number {pred_0}')
print(f'Actual number {actual_0}')

S_0_accuracy = accuracy(pred_0,actual_0)
S_0_accuracy

cm=confusion_matrix(actual_0, pred_0)
plt.figure(figsize=(10,10))
plot_confusion_matrix(cm, [str(i) for i in range(0,9)])

"""Fake digits evaluation (Sample = S1)"""

S_1 = next(iter(fake_digit_loader)) #S1 sample of fake digits loaded
imgs_1, lbls_1 = S_1

actual_1 = lbls_1[:100].numpy()

test_output_1,last_layer_1 = cnn(imgs_1[:100])
pred_1 = torch.max(test_output_1,1)[1].data.numpy().squeeze()

print(f'Prediction number {pred_1}')
print(f'Actual number {actual_1}')

S_1_accuracy = accuracy(pred_1,actual_1)
S_1_accuracy

cm=confusion_matrix(actual_1, pred_1)
plt.figure(figsize=(10,10))
plot_confusion_matrix(cm, [str(i) for i in range(0,9)])

!sudo pip install graphviz
!sudo pip install torchviz

from torchviz import make_dot

make_dot (cnn(imgs_0[:1]), params=dict(cnn.named_parameters()))

z = Variable(torch.randn(bs, z_dim).to(device))

make_dot (G(z[:1]), params=dict(G.named_parameters()))

s2 =  next(iter(loaders['train']))
imgs_0, lbls_0 = s2



make_dot (D(imgs_0[:1]), params=dict(D.named_parameters()))
