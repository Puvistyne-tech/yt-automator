import type { JsonObject, TemplateAudience } from "@/api/types";

export interface CannedIdea {
  name: string;
  description: string;
  reason: string;
  based_on: string[];
  definition: JsonObject;
  failsChecks?: boolean;
}

const TRENDS = {
  garden: "Building a tiny garden in a glass jar",
  sunset: "Why the sky turns orange at sunset",
  glow: "Ocean animals that glow in the dark",
  planes: "Easy paper planes that fly far",
  puzzles: "Rainy day puzzles for the whole family",
  bridges: "How bridges hold up heavy trucks",
  stretches: "Ten minute desk stretches",
  bicycle: "The history of the bicycle in eight minutes",
  food: "Trying street food from five cities",
  juggling: "Learning to juggle in one week",
};

const KIDS_IDEAS: CannedIdea[] = [
  {
    name: "Little sea lights",
    description: "Gentle stories about sea creatures that make their own light.",
    reason: "Glowing sea animals are popular, and they make calm bedtime stories.",
    based_on: [TRENDS.glow],
    definition: {
      structure: "story",
      brief: "A small fish meets a different glowing sea creature in each episode.",
      length: "short",
      tone: "Calm and wondering",
      topics: ["jellyfish", "lantern fish", "plankton"],
    },
  },
  {
    name: "Why is it so?",
    description: "Short answers to the questions children ask about the sky.",
    reason: "Videos explaining everyday sky colours are trending.",
    based_on: [TRENDS.sunset],
    definition: {
      structure: "explainer",
      brief: "One simple question about the sky, answered with a picture for every step.",
      tone: "Bright and simple",
      topics: ["sunsets", "rainbows", "clouds"],
    },
  },
  {
    name: "Things that fly",
    description: "Counting down the best flying things you can make at home.",
    reason: "Paper plane videos are popular with families this week.",
    based_on: [TRENDS.planes],
    definition: { structure: "countdown", brief: "Five things that fly, from good to amazing." },
  },
  {
    name: "Puzzle pals",
    description: "A friendly quiz with picture puzzles to solve together.",
    reason: "Family puzzle videos keep trending on rainy days.",
    based_on: [TRENDS.puzzles],
    definition: {
      structure: "quiz",
      brief: "Four picture puzzles with a hint before each answer.",
    },
    failsChecks: true,
  },
  {
    name: "Jar garden friends",
    description: "Tiny plants that grow in a jar, one at a time.",
    reason: "Small indoor gardens are trending and easy to show.",
    based_on: [TRENDS.garden],
    definition: { structure: "list", brief: "Five small plants and what each one needs." },
  },
  {
    name: "Bridge builders",
    description: "Stories about animals who build a bridge together.",
    reason: "Bridge videos are popular, and teamwork suits young viewers.",
    based_on: [TRENDS.bridges],
    definition: {
      structure: "story",
      brief: "Forest animals solve one crossing problem each time.",
    },
  },
  {
    name: "Wiggle breaks",
    description: "Short movement games to do between lessons.",
    reason: "Stretching videos are trending, and children love to move along.",
    based_on: [TRENDS.stretches],
    definition: { structure: "list", brief: "Five playful moves, each with a silly name." },
  },
];

const GENERAL_IDEAS: CannedIdea[] = [
  {
    name: "Engineering in plain words",
    description: "How everyday structures carry loads, explained step by step.",
    reason: "Videos about how bridges work are drawing large audiences.",
    based_on: [TRENDS.bridges],
    definition: {
      structure: "explainer",
      brief: "One structure per episode and the forces that keep it standing.",
      length: "standard",
      tone: "Clear and curious",
      topics: ["bridges", "towers", "tunnels"],
    },
  },
  {
    name: "Street food atlas",
    description: "A dish from a different city each episode and the story behind it.",
    reason: "Street food tours are among the most watched travel videos.",
    based_on: [TRENDS.food],
    definition: {
      structure: "list",
      brief: "Five dishes from one city and what makes each one local.",
      tone: "Warm and lively",
    },
  },
  {
    name: "Skill in a week",
    description: "Counting down the steps to learn a small skill in seven days.",
    reason: "Learn-it-fast challenges are trending.",
    based_on: [TRENDS.juggling],
    definition: {
      structure: "countdown",
      brief: "Seven daily steps, from first try to confident.",
    },
  },
  {
    name: "Inventions that changed travel",
    description: "Short histories of the machines that moved people.",
    reason: "Compact history videos about everyday inventions are popular.",
    based_on: [TRENDS.bicycle],
    definition: {
      structure: "explainer",
      brief: "One invention, where it came from and why it lasted.",
    },
    failsChecks: true,
  },
  {
    name: "Desk reset",
    description: "Quick routines to feel better after long hours at a desk.",
    reason: "Short wellbeing routines for office workers are trending.",
    based_on: [TRENDS.stretches],
    definition: { structure: "list", brief: "Five short routines with one clear benefit each." },
  },
  {
    name: "Sky science quiz",
    description: "Test what you know about light, colour and the atmosphere.",
    reason: "Sunset science videos are popular, and quizzes keep viewers watching.",
    based_on: [TRENDS.sunset, TRENDS.glow],
    definition: {
      structure: "quiz",
      brief: "Five questions about light in nature, then the answers.",
    },
  },
  {
    name: "Small spaces, green places",
    description: "Ideas for growing plants in very small homes.",
    reason: "Indoor garden builds are trending.",
    based_on: [TRENDS.garden],
    definition: { structure: "list", brief: "Five plants that thrive in small, bright spaces." },
  },
];

export const CANNED_IDEAS: Record<TemplateAudience, CannedIdea[]> = {
  kids: KIDS_IDEAS,
  general: GENERAL_IDEAS,
};
