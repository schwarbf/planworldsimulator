/** Example worlds on the landing page; the same four are seeded as featured worlds in the API. */
export interface ShowcaseWorld {
  name: string;
  premise: string;
  prompt: string;
  image: string;
}

export const SHOWCASE: ShowcaseWorld[] = [
  {
    name: "Fission Ops",
    premise: "Keep a reactor safe through heat waves and shift shortages.",
    prompt:
      "A nuclear power plant control room. Deliver 1 GW to the city for 90 days while keeping the core below 650 °C and every shift staffed.",
    image: "/showcase/fission-ops.png",
  },
  {
    name: "Bike Factory",
    premise: "Run a supply chain from tier-2 suppliers to three stores.",
    prompt:
      "A bike factory supply chain with tier 1 and tier 2 suppliers, a warehouse, an assembly plant and three stores.",
    image: "/showcase/bike-factory.png",
  },
  {
    name: "Grid Juggler",
    premise: "Balance a city's power grid as supply and demand shift.",
    prompt:
      "A city power grid with solar, wind and gas plants and a battery. Keep the lights on at the lowest cost.",
    image: "/showcase/grid-juggler.png",
  },
  {
    name: "Seven Seas",
    premise: "Route cargo ships across ports with storms and shifting prices.",
    prompt:
      "A shipping network across seven seas. Route cargo between ports to maximize profit while storms close lanes.",
    image: "/showcase/seven-seas.png",
  },
];
