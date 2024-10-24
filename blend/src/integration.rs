use futures::StreamExt;
use tokio::{select, spawn, sync::mpsc};

use crate::{
    network::{self, Network},
    tier1::{self, Tier1},
    tier2::{self, Tier2},
};

pub struct System {
    network: Network,
    tier1_input_channel: mpsc::UnboundedSender<tier1::Input>,
    tier1_output_channel: mpsc::UnboundedReceiver<tier1::Output>,
    tier2_input_channel: mpsc::UnboundedSender<tier2::Input>,
    tier2_output_channel: mpsc::UnboundedReceiver<tier2::Output>,
}

impl System {
    pub fn new() -> Self {
        let (tier1_input_sender, tier1_input_receiver) = mpsc::unbounded_channel();
        let (tier1_output_sender, tier1_output_receiver) = mpsc::unbounded_channel();
        let (tier2_input_sender, tier2_input_receiver) = mpsc::unbounded_channel();
        let (tier2_output_sender, tier2_output_receiver) = mpsc::unbounded_channel();

        let mut tier1 = Tier1::new(tier1_input_receiver, tier1_output_sender);
        spawn(async move { tier1.run().await });
        let mut tier2 = Tier2::new(tier2_input_receiver, tier2_output_sender);
        spawn(async move { tier2.run().await });

        Self {
            network: network::Network,
            tier1_input_channel: tier1_input_sender,
            tier1_output_channel: tier1_output_receiver,
            tier2_input_channel: tier2_input_sender,
            tier2_output_channel: tier2_output_receiver,
        }
    }

    pub async fn run(&mut self) {
        loop {
            select! {
                Some((msg, from)) = self.network.next() => {
                    self.tier1_input_channel.send(tier1::Input::FromNetwork { msg, from, });
                }
                Some(tier1_output) = self.tier1_output_channel.recv() => {
                    match tier1_output {
                        tier1::Output::ToNetwork { msg, exclude } => {
                            self.network.send_to_all(msg, exclude);
                        }
                        tier1::Output::ToTier2(msg) => {
                            self.tier2_input_channel.send(tier2::Input::FromTier1(msg));
                        }
                    }
                }
                Some(tier2_output) = self.tier2_output_channel.recv() => {
                    match tier2_output {
                        tier2::Output::ToTier1(msg) => {
                            self.tier1_input_channel.send(tier1::Input::FromTier2(msg));
                        }
                        tier2::Output::ToBroadcast(msg) => {
                            self.network.send_to_all(msg, None);
                        }
                    }
                }
            }
        }
    }
}
