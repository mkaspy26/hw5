// The secret-society identities for the five agents. The playful name is
// always shown next to a plain-English description of the real job.

import type { AgentName } from "./api";

export interface Member {
  agent: AgentName;
  codename: string;
  rank: string;
  sigil: string;
  color: string; // each agent's ink color in the feed and on its card
  meaning: string; // why this code name
  job: string; // precise, plain-English job description
}

export const SOCIETY: Record<AgentName, Member> = {
  Boss: {
    agent: "Boss",
    codename: "The Founder",
    rank: "No. 322 · Head of the Order",
    sigil: "☠",
    color: "#e2c275",
    meaning: "The one who founded the order and gives every order.",
    job: "Boss agent. Reads the ticket, hands work to the other four, sets the ticket's status, and writes the final verdict.",
  },
  Inventory: {
    agent: "Inventory",
    codename: "Ossuary",
    rank: "Keeper of the Vaults",
    sigil: "⚱",
    color: "#e8dfc8",
    meaning: "An ossuary is a vault where bones are stored, just as this agent keeps track of what's stored on the shelves.",
    job: "Inventory agent. Checks how many of an item are in stock per size, which vendor can restock it, and how long that takes. Can prepare a restock purchase for a human to approve.",
  },
  Accounting: {
    agent: "Accounting",
    codename: "Obol",
    rank: "Master of Coin",
    sigil: "⚖",
    color: "#86c79a",
    meaning: "An obol is the coin once placed with the dead to pay the ferryman, so it stands for every payment.",
    job: "Accounting agent. Checks cash and unpaid bills, does discount math, and prepares rent/invoice payments. It can't pay anything itself; a human approves.",
  },
  Facilities: {
    agent: "Facilities",
    codename: "Tombwarden",
    rank: "Guardian of the Tomb",
    sigil: "♜",
    color: "#9fb6d0",
    meaning: "The Tomb is the society's hall, and its warden guards the building. Here, the building is the shop.",
    job: "Facilities agent. Owns the shop space and lease: checks that a rent notice matches the lease and hasn't already been paid.",
  },
  "Customer Service": {
    agent: "Customer Service",
    codename: "Raven",
    rank: "Messenger to the Outside",
    sigil: "✒",
    color: "#bba3e6",
    meaning: "Ravens carry messages out of the castle. This agent writes the letters to customers.",
    job: "Customer Service agent. Drafts the reply to the customer using only facts from the database. It never sends anything; a human does.",
  },
};

export const ORDER: AgentName[] = ["Boss", "Inventory", "Accounting", "Facilities", "Customer Service"];

export const member = (agent: string): Member => SOCIETY[agent as AgentName] ?? SOCIETY.Boss;
