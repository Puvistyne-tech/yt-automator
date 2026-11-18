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
  {
    const: "custom",
    title: "Custom style",
    description: "Write your own art direction, colours, outlines and texture below.",
    "x-group": "Your own",
  },
];
