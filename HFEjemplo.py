from absl import app, flags,logging
import torch as th 
import  pytorch_lightning as pl 

import nlp 
import transformers

import sh


flags.DEFINE_integer('epochs',10,'')
flags.DEFINE_float('lr',1e-2,'')
flags.DEFINE_float('momentum',.9,'')
flags.DEFINE_string('model','bert-base-uncased','')
flags.DEFINE_integer('seq_length',6 ,'')
flags.DEFINE_boolean('debug',False,'')
flags.DEFINE_integer('samples',10,'')
flags.DEFINE_integer('batch_size',10,'')
flags.DEFINE_integer('ds_percent',100,'')

FLAGS=flags.FLAGS

sh.rm('-r','-f','logs')
sh.mkdir('logs')


class IMDBSentimentClassifier(pl.LightningModule): 
    def __init__(self):
        super().__init__()
        self.model = transformers.BertForSequenceClassification.from_pretrained(FLAGS.model)
        #self.model = transformers.BertForSequenceClassification.from_pretrained(FLAGS.model)    
        #import IPython ; IPython.embed() ; exit(1)
        self.loss=th.nn.CrossEntropyLoss(reduction='none')
   
    def prepare_data(self):
        tokenizer = transformers.BertTokenizer.from_pretrained(FLAGS.model)
        def _tokenize(x):
            x['input_ids']=tokenizer.encode(
                    x['text'],
                    max_length=FLAGS.seq_length,
                    pad_to_max_length=True)
            return x
        def _prepare_ds(split):
            ds = nlp.load_dataset('imdb',split=f'{split}[:{FLAGS.samples if FLAGS.debug else f"{FLAGS.ds_percent}%"}]') 
            #import IPython ; IPython.embed() ; exit(1)
            ds=ds.shuffle()
            #ds=ds[:1250]
            ds=ds.map(_tokenize)
            ds.set_format(type='torch',columns=['input_ids','label' ])
            return ds
        #self.train_ds=prepare_ds('train')
        #self.test_ds=prepare_ds('test')
        self.train_ds,self.test_ds=map(_prepare_ds,('train','test'))
    
    def forward(self,input_ids):
        mask=(input_ids!=0).float()
        #import IPython ; IPython.embed() ; exit(1)
        logits= self.model(input_ids,mask)['logits']    
        return logits
        #import IPython ; IPython.embed() ; exit(1) 
    
    def training_step(self, batch, batch_idx):  
        logits = self.forward(batch['input_ids'])
        #import IPython ; IPython.embed() ; exit(1) 
        loss = self.loss(logits, batch['label']).mean()
        return{'loss':loss , 'log':{'train_loss':loss}}
        
        #import IPython ; IPython.embed() ; exit(1)
    
    def validation_step(self, batch, batch_idx):
        logits = self.forward(batch['input_ids'])
        #import IPython ; IPython.embed() ; exit(1) 
        loss = self.loss(logits, batch['label'])
        acc = (logits.argmax(-1)==batch['label']).float()
        return {'loss':loss, 'acc':acc}
        #import IPython ; IPython.embed() ; exit(1)
    
    def validation_epoch_end(self, outputs): 
        loss=th.cat([o['loss'] for o in outputs],0).mean()
        acc=th.cat([o['acc'] for o in outputs],0).mean()
        out= {'val_loss':loss, 'val_acc':acc} 
        return {**out,'log':out}
     
    def train_dataloader(self):
        #import IPython; IPython.embed()
        return th.utils.data.DataLoader(
                self.train_ds,
                num_workers=4,
                batch_size=FLAGS.batch_size,
                shuffle=True,
                drop_last=True,

                )
    def val_dataloader(self):
        return th.utils.data.DataLoader(
                self.test_ds,
                num_workers=4,
                batch_size=FLAGS.batch_size,
                shuffle=False,
                drop_last=False,
                )
    def configure_optimizers(self):
        #import IPython ; IPython.embed() ; exit(1) 
        return th.optim.SGD(
            self.parameters(),
            lr=FLAGS.lr,
            momentum=FLAGS.momentum,
            )

def main(_):
    model=IMDBSentimentClassifier()
    trainer=pl.Trainer(
        default_root_dir='logs',
        gpus=(1 if th.cuda.is_available() else 0),
        max_epochs=FLAGS.epochs,
        fast_dev_run=FLAGS.debug,
        logger=pl.loggers.TensorBoardLogger('./logs/',name='imdb', version=0),
        )
    trainer.fit(model)

if __name__ == '__main__':
    app.run(main)
