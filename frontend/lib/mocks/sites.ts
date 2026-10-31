import type { SiteDetail } from "../types";

export const MOCK_SITES: SiteDetail[] = [
  {
    id: 1,
    name: "Rani ki Vav",
    region: "Gujarat",
    category: "stepwell",
    lat: 23.8593,
    lon: 72.1018,
    description:
      "Subterranean stepwell in Patan built in the 11th century by Queen Udayamati. Designed as an inverted temple honoring water sanctity with seven pillared terraces and over five hundred principal sculptures.",
    images: [
      {
        id: 101,
        url: "https://images.unsplash.com/photo-1599818818819-0f62fd1553c6?auto=format&fit=crop&w=1200&q=80",
        author: "K. Mehta",
        licence: "CC BY-SA 4.0",
        source_url: "https://commons.wikimedia.org/wiki/File:Rani_ki_vav.jpg",
        status: "processed",
        tags: [
          { id: 1, label: "stepwell", tag_type: "site_type", score: 0.94, status: "verified" },
          { id: 2, label: "carved pillars", tag_type: "feature", score: 0.82, status: "verified" },
          { id: 3, label: "sheshashayi vishnu", tag_type: "feature", score: 0.78, status: "auto" },
          { id: 4, label: "stepped pavilion", tag_type: "feature", score: 0.71, status: "added_by_human" },
        ],
      },
    ],
  },
  {
    id: 2,
    name: "Adalaj Stepwell",
    region: "Gujarat",
    category: "stepwell",
    lat: 23.1667,
    lon: 72.5801,
    description:
      "Five-storey subterranean well built in 1498 by Queen Rudadevi. Harmonious integration of Solanki architectural carving with Islamic floral fretwork, designed around octagonal light shafts.",
    images: [
      {
        id: 102,
        url: "https://images.unsplash.com/photo-1609137144813-7d9921338f24?auto=format&fit=crop&w=1200&q=80",
        author: "A. Patel",
        licence: "CC BY-SA 4.0",
        source_url: "https://commons.wikimedia.org/wiki/File:Adalaj_Stepwell.jpg",
        status: "processed",
        tags: [
          { id: 5, label: "stepwell", tag_type: "site_type", score: 0.91, status: "verified" },
          { id: 6, label: "octagonal shaft", tag_type: "feature", score: 0.85, status: "verified" },
          { id: 7, label: "jali work", tag_type: "feature", score: 0.69, status: "auto" },
          { id: 8, label: "stringcourse frieze", tag_type: "feature", score: 0.58, status: "rejected" },
        ],
      },
    ],
  },
  {
    id: 3,
    name: "Sun Temple, Modhera",
    region: "Gujarat",
    category: "temple",
    lat: 23.5835,
    lon: 72.1331,
    description:
      "11th-century Chaulukya temple complex beside the Pushpavati River. Features the Surya Kund stepped water tank flanked by miniature shrines, Sabha Mandapa assembly hall, and equinoctial alignment.",
    images: [
      {
        id: 103,
        url: "https://images.unsplash.com/photo-1624640196238-dcf2b92110c4?auto=format&fit=crop&w=1200&q=80",
        author: "V. Sharma",
        licence: "CC BY-SA 4.0",
        source_url: "https://commons.wikimedia.org/wiki/File:Modhera_Sun_Temple.jpg",
        status: "processed",
        tags: [
          { id: 9, label: "temple", tag_type: "site_type", score: 0.96, status: "verified" },
          { id: 10, label: "stepped tank", tag_type: "feature", score: 0.89, status: "verified" },
          { id: 11, label: "torana arch", tag_type: "feature", score: 0.74, status: "auto" },
          { id: 12, label: "sculptured plinth", tag_type: "feature", score: 0.64, status: "auto" },
        ],
      },
    ],
  },
  {
    id: 4,
    name: "Chand Baori",
    region: "Rajasthan",
    category: "stepwell",
    lat: 27.0071,
    lon: 76.6064,
    description:
      "One of India's deepest stepwells, built by King Chanda in Abhaneri between the 8th and 9th centuries. Composed of 3,500 chevron-patterned narrow steps descending 20 metres over 13 levels.",
    images: [
      {
        id: 104,
        url: "https://images.unsplash.com/photo-1598977123418-454555aa0b18?auto=format&fit=crop&w=1200&q=80",
        author: "R. Singh",
        licence: "CC BY-SA 4.0",
        source_url: "https://commons.wikimedia.org/wiki/File:Chand_Baori.jpg",
        status: "processed",
        tags: [
          { id: 13, label: "stepwell", tag_type: "site_type", score: 0.97, status: "verified" },
          { id: 14, label: "geometric stairs", tag_type: "feature", score: 0.92, status: "verified" },
          { id: 15, label: "arcaded corridors", tag_type: "feature", score: 0.76, status: "added_by_human" },
          { id: 16, label: "sandstone reservoir", tag_type: "feature", score: 0.65, status: "auto" },
        ],
      },
    ],
  },
  {
    id: 5,
    name: "Kumbhalgarh Fort",
    region: "Rajasthan",
    category: "fort",
    lat: 25.1479,
    lon: 73.5873,
    description:
      "15th-century Mewar citadel constructed by Rana Kumbha in the Aravalli Hills. Enclosed by a 36-kilometre defensive stone wall with seven fortified gates and massive rounded bastions.",
    images: [
      {
        id: 105,
        url: "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=1200&q=80",
        author: "H. Joshi",
        licence: "CC BY-SA 4.0",
        source_url: "https://commons.wikimedia.org/wiki/File:Kumbhalgarh_Fort.jpg",
        status: "processed",
        tags: [
          { id: 17, label: "fort", tag_type: "site_type", score: 0.95, status: "verified" },
          { id: 18, label: "defensive wall", tag_type: "feature", score: 0.88, status: "verified" },
          { id: 19, label: "rounded bastions", tag_type: "feature", score: 0.73, status: "auto" },
          { id: 20, label: "watchtower", tag_type: "feature", score: 0.54, status: "rejected" },
        ],
      },
    ],
  },
  {
    id: 6,
    name: "Mehrangarh Fort",
    region: "Rajasthan",
    category: "fort",
    lat: 26.2978,
    lon: 73.0185,
    description:
      "Imposing burnished red sandstone fortress towering 122 metres above Jodhpur, founded in 1459 by Rao Jodha. Features soaring curtain walls, expansive courtyards, and pierced stone jharokhas.",
    images: [
      {
        id: 106,
        url: "https://images.unsplash.com/photo-1590766940554-634a7ed41450?auto=format&fit=crop&w=1200&q=80",
        author: "N. Rathore",
        licence: "CC BY-SA 4.0",
        source_url: "https://commons.wikimedia.org/wiki/File:Mehrangarh_Fort.jpg",
        status: "processed",
        tags: [
          { id: 21, label: "fort", tag_type: "site_type", score: 0.98, status: "verified" },
          { id: 22, label: "sandstone battlement", tag_type: "feature", score: 0.86, status: "verified" },
          { id: 23, label: "carved jharokhas", tag_type: "feature", score: 0.79, status: "added_by_human" },
          { id: 24, label: "cliff bastion", tag_type: "feature", score: 0.67, status: "auto" },
        ],
      },
    ],
  },
];
