# -*- coding: utf-8 -*-
"""Untitled5.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1eTGbxZGy7RYyCPueZup4Lq-N9z-ZRjbb
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from keras.models import Model
from keras.layers import Input, Embedding, Dense, Masking
from keras.layers import Attention, LayerNormalization, Dropout
from keras.optimizers import Adam

from google.colab import drive
drive.mount('/content/drive')

import os
os.chdir("/content/drive/My Drive/Colab Notebooks/")
os.getcwd()

df=pd.read_csv('SinhalaData.csv')

df

spa_sentences = df["sinhala"] + "\t" + df["english"]

# Save the concatenated sentences to a text file
with open("spa.txt", "w", encoding="utf-8") as file:
    for sentence in spa_sentences:
        file.write(str(sentence) + "\n")

text_file ="spa.txt"

text_file ="spa.txt"
with open(text_file) as f:
  lines=f.read().split("\n")[:-1]

i=0
for line in lines:
  print(line)
  i=i+1
  if(i==20):
    break

for x in range(len(lines)-10,len(lines)):
  print(lines[x])

import random
import string
import re

text_pairs = []


for line in lines:
    if '\t' in line:
        english, sinhala = line.split("\t")
        sinhala = "[start]" + sinhala.strip() + "[end]"
        text_pairs.append((english.strip(), sinhala))
for i in range(3):
    print(random.choice(text_pairs))

import random
random.shuffle(text_pairs)

num_val_samples =int(0.15*len(text_pairs))
num_train_samples=len(text_pairs) -2* num_val_samples
train_pairs = text_pairs[:num_train_samples]
val_pairs = text_pairs[num_train_samples:num_train_samples + num_val_samples]
test_pairs = text_pairs[num_train_samples + num_val_samples:]

print("Total sentences:",len(text_pairs))
print("Training set size:",len(train_pairs))
print("Validation set size:",len(val_pairs))
print("Testing set size:",len(test_pairs))

len(train_pairs)+len(val_pairs)+len(test_pairs)

strip_chars = string.punctuation + "¿"
strip_chars = strip_chars.replace("[", "")
strip_chars = strip_chars.replace("]", "")

f"[{re.escape(strip_chars)}]"

from tensorflow import keras
from tensorflow.keras import layers
import tensorflow as tf
def custom_standardization(input_string):
  lowercase = tf.strings.lower(input_string)
  return tf.strings.regex_replace(
    lowercase, f"[{re.escape(strip_chars)}]", "")
vocab_size = 15000
sequence_length = 20
source_vectorization = layers.TextVectorization(
  max_tokens=vocab_size,
  output_mode="int",
  output_sequence_length=sequence_length,
)
target_vectorization = layers.TextVectorization(
  max_tokens=vocab_size,
  output_mode="int",
  output_sequence_length=sequence_length + 1,
  standardize=custom_standardization,
)
train_english_texts = [pair[0] for pair in train_pairs]
train_spanish_texts = [pair[1] for pair in train_pairs]

source_vectorization.adapt(train_english_texts)
target_vectorization.adapt(train_spanish_texts)

batch_size=64

def format_dataset(eng,spa):
  eng=source_vectorization(eng)
  spa=target_vectorization(spa)
  return({
      "english":eng,
      "sinhala":spa[:,:-1],
  },spa[:,1:])

def make_dataset(pairs):
  eng_texts, spa_texts =zip(*pairs)
  eng_texts =list(eng_texts)
  spa_texts =list(spa_texts)
  dataset = tf.data.Dataset.from_tensor_slices((eng_texts, spa_texts))
  dataset = dataset.batch(batch_size)
  dataset = dataset.map(format_dataset, num_parallel_calls=4)
  return dataset.shuffle(2048).prefetch(16).cache()

train_ds = make_dataset(train_pairs)
val_ds = make_dataset(val_pairs)

for inputs, targets in train_ds.take(1):
  print(f"inputs['english'].shape:{inputs['english'].shape}")
  print(f"inputs['sinhala'].shape:{inputs['sinhala'].shape}")
  print(f"targets.shape:{targets.shape}")

  inputs['english'].shape:  (64, 20)
  inputs['sinhala'].shape: (64, 20)
  targets.shape: (64, 20)
print(list(train_ds.as_numpy_iterator())[50])

import string
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

import tensorflow as tf
from tensorflow.keras import layers

class TransformerEncoder(layers.Layer):
    def __init__(self, embed_dim, dense_dim, num_heads, **kwargs):
        super().__init__(**kwargs)
        self.embed_dim = embed_dim
        self.dense_dim = dense_dim
        self.num_heads = num_heads
        self.attention = layers.MultiHeadAttention(
            num_heads=num_heads, key_dim=embed_dim)
        self.dense_proj = tf.keras.Sequential([
            layers.Dense(dense_dim, activation="relu"),
            layers.Dense(embed_dim),
        ])
        self.layernorm_1 = layers.LayerNormalization()
        self.layernorm_2 = layers.LayerNormalization()

    def call(self, inputs, mask=None):
        if mask is not None:
            mask = mask[:, tf.newaxis, :]
        attention_output = self.attention(
            inputs, inputs, attention_mask=mask)
        proj_input = self.layernorm_1(inputs + attention_output)
        proj_output = self.dense_proj(proj_input)
        return self.layernorm_2(proj_input + proj_output)

    def get_config(self):
        config = super().get_config()
        config.update({
            "embed_dim": self.embed_dim,
            "num_heads": self.num_heads,
            "dense_dim": self.dense_dim,
        })
        return config

import tensorflow as tf
from tensorflow.keras import layers

class TransformerDecoder(layers.Layer):
    def __init__(self, embed_dim, dense_dim, num_heads, **kwargs):
        super().__init__(**kwargs)
        self.embed_dim = embed_dim
        self.dense_dim = dense_dim
        self.num_heads = num_heads
        self.attention_1 = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)
        self.attention_2 = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)
        self.dense_proj = tf.keras.Sequential([
            layers.Dense(dense_dim, activation="relu"),
            layers.Dense(embed_dim),
        ])
        self.layernorm_1 = layers.LayerNormalization()
        self.layernorm_2 = layers.LayerNormalization()
        self.layernorm_3 = layers.LayerNormalization()
        self.supports_masking = True

    def get_config(self):
        config = super().get_config()
        config.update({
            "embed_dim": self.embed_dim,
            "num_heads": self.num_heads,
            "dense_dim": self.dense_dim,
        })
        return config

    def get_causal_attention_mask(self, inputs):
        input_shape = tf.shape(inputs)
        batch_size, sequence_length = input_shape[0], input_shape[1]
        i = tf.range(sequence_length)[:, tf.newaxis]
        j = tf.range(sequence_length)
        mask = tf.cast(i >= j, dtype="int32")
        mask = tf.reshape(mask, (1, input_shape[1], input_shape[1]))
        mult = tf.concat([tf.expand_dims(batch_size, -1), tf.constant([1, 1], dtype=tf.int32)], axis=0)
        return tf.tile(mask, mult)

    def call(self, inputs, encoder_outputs, mask=None):
        causal_mask = self.get_causal_attention_mask(inputs)
        if mask is not None:
            padding_mask = tf.cast(mask[:, tf.newaxis, :], dtype="int32")
            padding_mask = tf.minimum(padding_mask, causal_mask)
        else:
            padding_mask = mask
        attention_output_1 = self.attention_1(
            query=inputs,
            value=inputs,
            key=inputs,
            attention_mask=causal_mask
        )
        attention_output_1 = self.layernorm_1(inputs + attention_output_1)
        attention_output_2 = self.attention_2(
            query=attention_output_1,
            value=encoder_outputs,
            key=encoder_outputs,
            attention_mask=padding_mask,
        )
        attention_output_2 = self.layernorm_2(attention_output_1 + attention_output_2)
        proj_output = self.dense_proj(attention_output_2)
        return self.layernorm_3(attention_output_2 + proj_output)

import tensorflow as tf
from tensorflow.keras import layers

class PositionalEmbedding(layers.Layer):
    def __init__(self, sequence_length, input_dim, output_dim, **kwargs):
        super().__init__(**kwargs)
        self.token_embeddings = layers.Embedding(input_dim=input_dim, output_dim=output_dim)
        self.position_embeddings = layers.Embedding(input_dim=sequence_length, output_dim=output_dim)
        self.sequence_length = sequence_length
        self.input_dim = input_dim
        self.output_dim = output_dim

    def call(self, inputs):
        length = tf.shape(inputs)[-1]
        positions = tf.range(start=0, limit=length, delta=1)
        embedded_tokens = self.token_embeddings(inputs)
        embedded_positions = self.position_embeddings(positions)
        return embedded_tokens + embedded_positions

    def compute_mask(self, inputs, mask=None):
        return tf.math.not_equal(inputs, 0)

    def get_config(self):
        config = super(PositionalEmbedding, self).get_config()
        config.update({
            "output_dim": self.output_dim,
            "sequence_length": self.sequence_length,
            "input_dim": self.input_dim,
        })
        return config

embed_dim = 256
dense_dim = 2048
num_heads = 8


# Define the encoder inputs
encoder_inputs = tf.keras.Input(shape=(None,), dtype="int64", name="english")

# Add positional embedding to the encoder inputs
x = PositionalEmbedding(sequence_length, vocab_size, embed_dim)(encoder_inputs)

# Encode the inputs using TransformerEncoder
encoder_outputs = TransformerEncoder(embed_dim, dense_dim, num_heads)(x)

# Define the decoder inputs
decoder_inputs = tf.keras.Input(shape=(None,), dtype="int64", name="sinhala")

# Add positional embedding to the decoder inputs
x = PositionalEmbedding(sequence_length, vocab_size, embed_dim)(decoder_inputs)

# Decode the inputs using TransformerDecoder
x = TransformerDecoder(embed_dim, dense_dim, num_heads)(x, encoder_outputs)

# Apply dropout
x = layers.Dropout(0.5)(x)

# Generate decoder outputs
decoder_outputs = layers.Dense(vocab_size, activation="softmax")(x)

# Create the transformer model
transformer = tf.keras.Model([encoder_inputs, decoder_inputs], decoder_outputs)

transformer.summary()

transformer.compile(optimizer="rmsprop",
                    loss="sparse_categorical_crossentropy",
                    metrics=["accuracy"])

transformer.fit(train_ds, epochs=30, validation_data=val_ds)

import numpy as np

# Define the vocabulary and index lookup for Spanish
spa_vocab = target_vectorization.get_vocabulary()
spa_index_lookup = dict(zip(range(len(spa_vocab)), spa_vocab))
max_decoded_sentence_length = 20

def decode_sequence(input_sentence):
    tokenized_input_sentence = source_vectorization([input_sentence])
    decoded_sentence = "[start]"

    for i in range(max_decoded_sentence_length):
        tokenized_target_sentence = target_vectorization([decoded_sentence])[:, :-1]
        predictions = transformer([tokenized_input_sentence, tokenized_target_sentence])
        sampled_token_index = np.argmax(predictions[0, i, :])
        sampled_token = spa_index_lookup[sampled_token_index]
        decoded_sentence += " " + sampled_token

        if sampled_token == "[end]":
            break

    return decoded_sentence

test_eng_texts = [pair[0] for pair in test_pairs]

for _ in range(20):
    input_sentence = random.choice(test_eng_texts)
    print("-")
    print(input_sentence)
    print(decode_sequence(input_sentence))

import numpy as np

# Define the vocabulary and index lookup for Sinhala
sin_vocab = target_vectorization.get_vocabulary()
sin_index_lookup = dict(zip(range(len(sin_vocab)), sin_vocab))
max_decoded_sentence_length = 20

def decode_sequence(input_sentence):
    tokenized_input_sentence = source_vectorization([input_sentence])
    decoded_sentence = "[start]"

    for i in range(max_decoded_sentence_length):
        tokenized_target_sentence = target_vectorization([decoded_sentence])[:, :-1]
        predictions = transformer([tokenized_input_sentence, tokenized_target_sentence])
        sampled_token_index = np.argmax(predictions[0, i, :])
        sampled_token = sin_index_lookup[sampled_token_index]
        decoded_sentence += " " + sampled_token

        if sampled_token == "[end]":
            break

    return decoded_sentence

test_eng_texts = [pair[0] for pair in test_pairs]

for _ in range(20):
    input_sentence = random.choice(test_eng_texts)
    print("-")
    print("English: ", input_sentence)
    print("Sinhala: ", decode_sequence(input_sentence))

import numpy as np

# Define the vocabulary and index lookup for Sinhala
sin_vocab = target_vectorization.get_vocabulary()
sin_index_lookup = dict(zip(range(len(sin_vocab)), sin_vocab))
max_decoded_sentence_length = 20

def decode_sequence(input_sentence):
    tokenized_input_sentence = source_vectorization([input_sentence])
    decoded_sentence = "[start]"

    for i in range(max_decoded_sentence_length):
        tokenized_target_sentence = target_vectorization([decoded_sentence])[:, :-1]
        predictions = transformer([tokenized_input_sentence, tokenized_target_sentence])
        sampled_token_index = np.argmax(predictions[0, i, :])
        sampled_token = sin_index_lookup[sampled_token_index]
        decoded_sentence += " " + sampled_token

        if sampled_token == "[end]":
            break

    return decoded_sentence

# Get English input from the user
input_sentence = input("Enter an English sentence: ")

# Translate the input sentence to Sinhala
translated_sentence = decode_sequence(input_sentence)

# Print the translated sentence
print("Sinhala translation:", translated_sentence)