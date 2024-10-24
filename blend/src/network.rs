use std::{
    pin::Pin,
    task::{Context, Poll},
};

use futures::Stream;

use crate::PeerId;

pub struct Network;

impl Network {
    pub fn send_to_all(&self, msg: Vec<u8>, exclude: Option<PeerId>) {
        todo!("send the msg to all peers except the one with the given id")
    }
}

impl Stream for Network {
    type Item = (Vec<u8>, PeerId);

    fn poll_next(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        todo!("Return messages received from peers")
    }
}
