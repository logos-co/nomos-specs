use std::{
    pin::Pin,
    task::{Context, Poll},
};

use futures::{Stream, StreamExt};
use tokio::{select, sync::mpsc};

use crate::PeerId;

pub struct Tier1 {
    input_channel: mpsc::UnboundedReceiver<Input>,
    output_channel: mpsc::UnboundedSender<Output>,

    persitent_transmitter: PersistentTransmitter,
}

pub enum Input {
    FromNetwork { msg: Vec<u8>, from: PeerId },
    FromTier2(Vec<u8>),
}

pub enum Output {
    ToNetwork {
        msg: Vec<u8>,
        exclude: Option<PeerId>,
    },
    ToTier2(Vec<u8>),
}

impl Tier1 {
    pub fn new(
        input_channel: mpsc::UnboundedReceiver<Input>,
        output_channel: mpsc::UnboundedSender<Output>,
    ) -> Self {
        Self {
            input_channel,
            output_channel,
            persitent_transmitter: todo!(),
        }
    }

    pub async fn run(&mut self) {
        loop {
            select! {
                Some(input) = self.input_channel.recv() => {
                    match input {
                        Input::FromNetwork { msg, from } => {
                            // TODO: Send to monitor
                            if self.is_drop_message(&msg) {
                                continue;
                            }
                            if self.is_duplicate(&msg) {
                                continue;
                            }
                            self.output_channel.send(Output::ToNetwork { msg: msg.clone(), exclude: Some(from) });
                            self.output_channel.send(Output::ToTier2(msg));
                        }
                        Input::FromTier2(msg) => {
                            self.persitent_transmitter.push(msg);
                        }
                    }
                }
                Some(msg_to_emit) = self.persitent_transmitter.next() => {
                    self.output_channel.send(Output::ToNetwork { msg: msg_to_emit, exclude: None });
                }

            }
        }
    }

    fn is_drop_message(&self, msg: &[u8]) -> bool {
        todo!()
    }

    fn is_duplicate(&self, msg: &[u8]) -> bool {
        todo!()
    }
}

struct PersistentTransmitter {
    max_emission_frequency: f64,
    drop_message_probability: f64,
}

impl PersistentTransmitter {
    fn push(&self, msg: Vec<u8>) {
        todo!("Push msg to the buffer (queue)")
    }
}

impl Stream for PersistentTransmitter {
    type Item = Vec<u8>;

    fn poll_next(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        todo!("Periodically release one of scheduled messages. Release a drop message with the probability if no message scheduled")
    }
}
