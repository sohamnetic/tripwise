import type { Plan } from "../api/types";
import { vibeFor } from "./vibes";

export interface PackGroup {
  title: string;
  items: string[];
}

// A sensible packing list from where you're going, when, how, and what you'll do.
export function packingList(plan: Plan): PackGroup[] {
  const { request: req, destination, outbound } = plan;
  const scene = vibeFor(destination.name).scene;
  const month = new Date(`${req.start_date}T00:00:00`).getMonth(); // 0 = Jan
  const winter = month >= 10 || month <= 1;
  const monsoon = month >= 5 && month <= 8;
  const has = (i: string) => req.interests.includes(i as never);

  const essentials = ["ID proof (+ a photo on your phone)", "Phone charger & power bank", "Basic medicines & any prescriptions", "Reusable water bottle", "Some cash for small shops & autos"];
  if (destination.international) essentials.unshift("Passport & visa documents", "Travel insurance", "Universal plug adapter");

  const clothes = ["Comfortable walking shoes", "Enough clothes for " + (plan.summary.nights + 1) + " days"];
  if (scene === "beach") clothes.push("Swimwear", "Flip-flops", "Sunglasses & a hat", "Sunscreen (SPF 30+)");
  if (scene === "hills") clothes.push(winter ? "Heavy jacket, thermals & gloves" : "Fleece or light jacket", "Warm socks", "Lip balm & moisturiser");
  if (scene === "heritage" || scene === "river") clothes.push("Scarf or stole (covers shoulders in temples)", "Cap & sunglasses");
  if (winter && scene !== "beach" && scene !== "hills") clothes.push("A sweater for cool evenings");
  if (monsoon) clothes.push("Umbrella or rain jacket", "Quick-dry clothes");

  const extras: string[] = [];
  if (outbound.mode === "train") extras.push("Chain & lock for luggage", "Snacks for the journey", "Earplugs & an eye mask");
  if (outbound.mode === "bus") extras.push("Neck pillow", "Motion-sickness tablets");
  if (outbound.mode === "flight") extras.push("Web check-in 24–48h before", "Liquids under 100 ml in cabin bag");
  if (has("adventure")) extras.push("Sports shoes with grip", "Dry bag for phone");
  if (has("nature")) extras.push("Mosquito repellent");
  if (has("nightlife")) extras.push("One smart outfit for the evening");
  if (has("shopping")) extras.push("A foldable extra bag for shopping");

  return [
    { title: "Essentials", items: essentials },
    { title: "Clothes & comfort", items: clothes },
    { title: "For this trip", items: extras },
  ].filter((g) => g.items.length);
}
