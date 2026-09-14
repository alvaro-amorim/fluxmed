const routeColors = ['#0f6973', '#b86f2b', '#5264a3', '#8a557f', '#447a52', '#8b6b2f']

export function routeColor(index: number): string {
  return routeColors[index % routeColors.length]
}
