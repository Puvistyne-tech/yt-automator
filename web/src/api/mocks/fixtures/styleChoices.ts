function styleCard(value: string, title: string, group: string, swatches: string[]) {
  return {
    const: value,
    title,
    description: `Every picture drawn as ${title.toLowerCase()}.`,
    "x-group": group,
    "x-swatches": swatches,
  };
}

export const STYLE_CHOICES = [
  styleCard("watercolour_storybook", "Watercolour storybook", "Illustrated", [
    "#A9D3EE",
    "#CFE8C0",
    "#A8D5BA",
    "#7FB89A",
    "#F3A69A",
  ]),
  styleCard("animated_3d", "3D animated film", "Animated", [
    "#8ED1F5",
    "#A6E08F",
    "#6CC46A",
    "#3F9B55",
    "#FFB84D",
  ]),
  styleCard("crayon_drawing", "Crayon drawing", "Hand-drawn", [
    "#FFFFFF",
    "#8AC926",
    "#FFB703",
    "#219EBC",
    "#E63946",
  ]),
  styleCard("claymation", "Claymation", "Crafted", [
    "#BFE0E8",
    "#E9C46A",
    "#8AB17D",
    "#2A9D8F",
    "#E76F51",
  ]),
  {
    const: "custom",
    title: "Custom style",
    description: "Write your own art direction.",
    "x-group": "Your own",
  },
];
