use std::{
    pin::Pin,
    task::{Context, Poll},
};

use futures::{Stream, StreamExt};
use tokio::{select, sync::mpsc};

pub struct Tier2 {
    input_channel: mpsc::UnboundedReceiver<Input>,
    output_channel: mpsc::UnboundedSender<Output>,

    crypto_processor: CryptographicProcessor,
    temporal_processor: TemporalProcessor,
}

pub enum Input {
    FromTier1(Vec<u8>),
    New(Vec<u8>),
    FromTier3(Vec<u8>),
}

pub enum Output {
    ToTier1(Vec<u8>),
    ToBroadcast(Vec<u8>),
}

impl Tier2 {
    pub fn new(
        input_channel: mpsc::UnboundedReceiver<Input>,
        output_channel: mpsc::UnboundedSender<Output>,
    ) -> Self {
        Self {
            input_channel,
            output_channel,
            crypto_processor: todo!(),
            temporal_processor: todo!(),
        }
    }

    pub async fn run(&mut self) {
        loop {
            select! {
                Some(input) = self.input_channel.recv() => {
                    match input {
                        Input::FromTier1(msg) | Input::FromTier3(msg) => {
                            match self.crypto_processor.unwrap(msg) {
                                Ok(unwrapped) => self.temporal_processor.push(unwrapped),
                                Err(_) => {} // do nothing
                            }
                        }
                        Input::New(msg) => {
                            let wrapped = self.crypto_processor.wrap(msg);
                            self.output_channel.send(Output::ToTier1(wrapped));
                        }
                    }
                }
                Some(msg) = self.temporal_processor.next() => {
                    if msg.fully_unwrapped {
                        self.output_channel.send(Output::ToBroadcast(msg.msg));
                    } else {
                        self.output_channel.send(Output::ToTier1(msg.msg));
                    }
                }
            }
        }
    }
}

struct CryptographicProcessor;

struct CryptoError;

impl CryptographicProcessor {
    fn wrap(&self, msg: Vec<u8>) -> Vec<u8> {
        todo!()
    }

    fn unwrap(&self, msg: Vec<u8>) -> Result<UnwrappedMessage, CryptoError> {
        todo!()
    }
}

struct UnwrappedMessage {
    msg: Vec<u8>,
    fully_unwrapped: bool,
}

struct TemporalProcessor {
    max_delay: u64,
}

impl TemporalProcessor {
    fn push(&self, msg: UnwrappedMessage) {
        todo!("Push msg to the buffer (queue)")
    }
}

impl Stream for TemporalProcessor {
    type Item = UnwrappedMessage;

    fn poll_next(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        todo!("Run the logic and release a message when necessary")
    }
}
