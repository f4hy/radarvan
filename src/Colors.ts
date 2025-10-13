export function TeamColor(name: string) {
  switch (name) {
    case "1":
    case "Modus":
    case "Brendan":
    case "jbb":
    case "Jared":
      return "#82ca9d"
    case "3":
    case "OneThree111":
    case "Bill":
    case "Ye_Ole_Seans":
    case "Sean":
      return "#8884d8"
    default:
      return "#444444"
  }
}

export function PlayerColor(name: string) {
  const loname = name.toLocaleLowerCase()
  switch (loname) {
    case "1":
    case "modus":
    case "brendan":
      return "#ff9aeb"
    case "jbb":
    case "jared":
      return "#3ed12e"
    case "3":
    case "onethree111":
    case "bill":
      return "#9528bd"
    case "ye_ole_seans":
    case "sean":
      return "#e5de0e"
    default:
      return "#444444"
  }
}

const chartColors: string[] = [
  '#4E79A7', // Blue
  '#F28E2B', // Orange
  '#E15759', // Red
  '#76B7B2', // Teal
  '#59A14F', // Green
  '#EDC948', // Yellow
  '#B07AA1', // Purple
  '#FF9DA7', // Pink
];
export function ColorByIdx(idx: number) {
  return chartColors[idx % chartColors.length]
}
