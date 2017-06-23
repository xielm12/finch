import torch
import numpy as np
import math
import tensorflow as tf
from sklearn.utils import shuffle


class ConvLSTMClassifier(torch.nn.Module):
    def __init__(self, seq_len, vocab_size, n_out=2, embedding_dim=128, n_filters=64, kernel_size=5, pool_size=4,
                 cell_size=70):
        super(ConvLSTMClassifier, self).__init__()
        self.seq_len = seq_len
        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim
        self.n_filters = n_filters
        self.kernel_size = kernel_size
        self.pool_size = pool_size
        self.cell_size = cell_size
        self.n_out = n_out
        self.build_model()
    # end constructor


    def build_model(self):
        self.encoder = torch.nn.Embedding(self.vocab_size, self.embedding_dim)
        self.conv1d = torch.nn.Conv1d(in_channels = self.embedding_dim,
                                      out_channels = self.n_filters,
                                      kernel_size = self.kernel_size)
        self.pooling = torch.nn.MaxPool1d(kernel_size = self.pool_size)
        self.lstm = torch.nn.LSTM(input_size = self.n_filters,
                                  hidden_size = self.cell_size,
                                  batch_first = True)
        self.fc = torch.nn.Linear(self.cell_size, self.n_out)
        self.criterion = torch.nn.CrossEntropyLoss()
        self.optimizer = torch.optim.Adam(self.parameters())
    # end method build_model    


    def forward(self, X, batch_size):
        embedded = self.encoder(X)
        conv_out = self.conv1d(embedded.permute(0, 2, 1))
        pool_out = self.pooling(conv_out)
        lstm_out, _ = self.lstm(pool_out.permute(0, 2, 1), None)
        reshaped = lstm_out[:, -1, :]
        logits = self.fc(reshaped)
        return logits
    # end method forward


    def fit(self, X, y, n_epoch=10, batch_size=32):
        global_step = 0
        n_batch = int(len(X) / batch_size)
        total_steps = int(n_epoch * n_batch)
        for epoch in range(n_epoch):
            X, y = shuffle(X, y)
            state = None
            for local_step, (X_, y_) in enumerate(zip(self.gen_batch(X, batch_size),
                                                      self.gen_batch(y, batch_size))):
                X_batch = torch.autograd.Variable(torch.from_numpy(X_.astype(np.int64)))
                y_batch = torch.autograd.Variable(torch.from_numpy(y_.astype(np.int64)))
                y_pred = self.forward(X_batch, len(X_))

                loss = self.criterion(y_pred, y_batch)     # cross entropy loss
                self.optimizer, lr = self.adjust_lr(self.optimizer, global_step, total_steps)
                self.optimizer.zero_grad()                             # clear gradients for this training step
                loss.backward()                                        # backpropagation, compute gradients
                self.optimizer.step()                                  # apply gradients
                global_step += 1
                acc = (torch.max(y_pred,1)[1].data.numpy().squeeze() == y_).mean()
                if local_step % 100 == 0:
                    print ('Epoch [%d/%d] | Step [%d/%d] | Loss: %.4f | Acc: %.4f | LR: %.4f'
                           %(epoch+1, n_epoch, local_step, n_batch, loss.data[0], acc, lr))
    # end method fit


    def evaluate(self, X_test, y_test, batch_size=32):
        correct = 0
        total = 0
        state = None
        for X_, y_ in zip(self.gen_batch(X_test, batch_size), self.gen_batch(y_test, batch_size)):
            X_batch = torch.autograd.Variable(torch.from_numpy(X_.astype(np.int64)))
            y_batch = torch.from_numpy(y_.astype(np.int64))
            y_pred = self.forward(X_batch, len(X_))
            _, y_pred = torch.max(y_pred.data, 1)
            total += y_batch.size(0)
            correct += (y_pred == y_batch).sum()
        print('Test Accuracy of the model: %.4f' % (float(correct) / total)) 
    # end method evaluate


    def gen_batch(self, arr, batch_size):
        for i in range(0, len(arr), batch_size):
            yield arr[i : i + batch_size]
    # end method gen_batch


    def adjust_lr(self, optimizer, current_step, total_steps):
        max_lr = 0.003
        min_lr = 0.0001
        decay_rate = math.log(min_lr/max_lr) / (-total_steps)
        lr = max_lr * math.exp(-decay_rate * current_step)
        for param_group in optimizer.param_groups:
            param_group['lr'] = lr
        return optimizer, lr
    # end method adjust_lr
# end class RNNClassifier
