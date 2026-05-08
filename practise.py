#transformers Architecture
#1.self Attention mechanism
# starting layer of transformer architecture  it allows the transformer model to determine which words in a sentense that are most relevant to each other
#this is done using scalar dot products
#Query (Q)
#Key(K)
#Value(V)
#2 multihead attention
#instead of single attention mechanism,transformers uses multiple attentions heads
#running in parallel.each captures differnt aspects 
#3Position Encoding
#position encoding in Transformers injects token order information into input embeddings ,as self attention process tokens in parallel and lacks inherit sequential awareness
#it adds a uique fixed or learnable vector to each word embedding,enabling the model to distinguish word positions and captures sentense structure
# Position wise feed forward networkss
#this feed forward networks consist of two liner transformations with a Relu activation.it is applied independenlty to each position in the sequence .This transformations helps refine the encoded representations at each position 
#4.embeddings transformers cannot work with raw words as they need numbers ,so each inut token is converted into a vector ,called an embedding.
# this embeddings are trainable ,meaning the model learns the best numeric representation for each token
#5Transformer encoder and decoder Architecture


#underestanding transformer architecture with sample example
#1.text->Tokenization->token ids->embeddings->position encoding->multihead attention->feedd forward neural network->output probababilities
#input text;"I love playing cricket"
#2.tokenization->["I","love","playing","cricket"]
#token ids->[101,102,203,104]
#3.embeddings
#each token id is converted into a dense vectorrepresentation for example 101->[0.1,0.2,0.3]
#4.position encoding
#each token embedding is added with a position encoding vector to inject positional information for example 101->[0.1,0.2,0.3]+[0.01,0.02,0.03]=[0.11,0.22,0.33]
#final input =embedding + position vector
#5.self attention
#it calculated attention score between each token and other tokens in the sequence for example attention score between "I" and "love" might be high as they are closely related in the context of sentense
#6.multihead attention
#in multihead attention the model uses multiple multiple attention heads to capture different relation ships
#7.feed forward neural network
#after attention each token passes through a small neutal network to refine the representation
#linear-> Relu->linear
#8.add & Normalize(Residual connections)
#each layer does #Output=LayerNorm(input+Attention Output)

# explaining how this vector embddings is converted from tokens
#