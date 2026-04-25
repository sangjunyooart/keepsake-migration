"""
Generates ~20 synthetic natural-history chunks for corpus/processed/environmental_time/
so the trainer can run end-to-end without real corpus data.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CHUNKS = [
    (
        "Spring arrives slowly in the northern forests, announced first by the melting of snow along south-facing "
        "slopes. The birch trees are the earliest to show green, their catkins releasing pollen before the leaves "
        "have fully unfurled. In the understory, wood anemones push through last year's leaf litter, each bloom "
        "tracking the arc of the sun across the sky. The soil temperature rises by two or three degrees over the "
        "course of a week, triggering the emergence of earthworms and the first tentative forays of hibernating "
        "beetles. Migratory birds arrive in waves, each species keyed to a precise thermal threshold that has been "
        "calibrated over thousands of generations. The whole forest seems to hold its breath between thaw and "
        "the first genuine warmth, poised on the threshold of renewal."
    ),
    (
        "Monsoon season transforms the coastal lowlands of East Asia within days of its arrival. The humidity rises "
        "sharply and visibility drops as moisture-laden air sweeps in from the Pacific. Rice paddies that have sat "
        "fallow since autumn fill with water and are planted in synchrony with the rains. Frogs emerge in enormous "
        "numbers, their choruses audible for kilometers on still nights. The rivers swell and carry topsoil from "
        "hillsides deforested over centuries of cultivation. Farmers who have tracked these patterns for generations "
        "can predict the onset of the rains within a few days based on the behavior of swallows and the direction "
        "of evening clouds. The monsoon is not merely weather — it is the temporal backbone of agriculture, culture, "
        "and ecology across an entire hemisphere."
    ),
    (
        "Autumn in temperate deciduous forests is a period of controlled senescence. The shortening days and cooling "
        "nights trigger a cascade of biochemical events in the leaves: chlorophyll breaks down, unmasking the yellows "
        "of xanthophylls that were present all summer, while new anthocyanin pigments produce the reds and purples "
        "of maple and sumac. The trees are not dying — they are preparing. Nutrients are withdrawn from the leaves "
        "and stored in roots and bark. Sugars are converted to starch. Abscission layers form at the base of each "
        "petiole, and with the first hard frost the leaves release. The forest floor becomes a mosaic of color, "
        "slowly compressed by rain into a thick duff layer that will insulate the soil through winter."
    ),
    (
        "The tidal cycle governs life along rocky intertidal shores with a precision that seems almost mechanical. "
        "Organisms partition the intertidal zone by their tolerance for desiccation: barnacles highest, mussels and "
        "sea anemones in the middle, sea stars and urchins lowest. Twice daily, the receding tide exposes these "
        "communities to air, sun, and temperature extremes that would kill most marine organisms. Yet each species "
        "has evolved a suite of physiological and behavioral responses — closing valves, clustering together, "
        "retreating under ledges — that allow survival. The rhythm of tides is imposed by the gravitational pull "
        "of the moon and sun, making intertidal ecology a direct expression of celestial mechanics at the scale "
        "of individual organisms."
    ),
    (
        "Winter dormancy in deciduous trees is a state of suspended animation that can last five months in northern "
        "latitudes. The tree does not merely stop growing — it actively prepares for cold, synthesizing antifreeze "
        "compounds and withdrawing water from cells to prevent ice crystal formation. The buds are sealed with "
        "resinous scales and contain the compressed blueprint of next year's leaves and flowers. Beneath the snow, "
        "mycorrhizal fungi continue slow metabolic activity, maintaining connections between root systems. The "
        "apparent stillness of the winter forest conceals enormous biochemical complexity — a waiting that is "
        "not passive but purposeful, timed to the lengthening of days that begins imperceptibly at the winter "
        "solstice and builds toward the explosive growth of spring."
    ),
    (
        "The Pacific flyway carries millions of shorebirds along the western coast of the Americas twice each year. "
        "In spring, sanderlings and dunlins that wintered in Chile and Argentina move north toward breeding grounds "
        "in the Arctic tundra, stopping at critical refueling sites along the way. The birds arrive thin and "
        "hungry, their fat reserves nearly depleted by transoceanic flights. They feed intensively on invertebrates "
        "in the intertidal and then continue north, sometimes doubling their body weight in a week before departing "
        "again. The timing of these migrations is extraordinarily precise, synchronized across populations by "
        "photoperiod and endogenous circadian rhythms that have been refined by selection over millions of years "
        "of glacial cycling."
    ),
    (
        "Volcanic islands emerge from the ocean as bare rock and are colonized by life in a sequence that ecologists "
        "call primary succession. The first colonizers are cyanobacteria and lichens that can etch mineral nutrients "
        "from bare basalt. These pioneers create the conditions for mosses, which retain moisture and add organic "
        "matter to what will eventually become soil. Ferns follow, their spores carried by wind from distant shores. "
        "Over centuries, the succession moves toward forest, though the composition of that forest depends on "
        "which seeds arrive and when. On oceanic islands far from continental sources, this process can take "
        "thousands of years, and the resulting ecosystems are often profoundly different from any mainland analog."
    ),
    (
        "The Kuroshio Current sweeps northward along the eastern coast of Japan, carrying warm tropical water into "
        "temperate latitudes. It moderates the climate of coastal regions, producing milder winters and earlier "
        "springs than would otherwise occur at those latitudes. The current also transports larval fish and "
        "invertebrates northward, connecting marine ecosystems across thousands of kilometers. Where the Kuroshio "
        "meets the cold Oyashio Current from the north, nutrient-rich upwelling supports some of the most "
        "productive fishing grounds in the world. The boundary between the two currents shifts seasonally and "
        "interannually, driven by the same climate oscillations that affect rainfall patterns across Asia and "
        "the Americas."
    ),
    (
        "Permafrost underlies nearly a quarter of the northern hemisphere's land surface, storing vast quantities "
        "of organic carbon that accumulated over thousands of years of plant growth in cold, waterlogged soils. "
        "As long as temperatures remain below freezing, this carbon is locked away. But as Arctic temperatures "
        "rise at twice the global average rate, the permafrost is thawing. The organic matter decomposes, "
        "releasing carbon dioxide and methane into the atmosphere. Thermokarst lakes form where ice-rich soils "
        "collapse. Coastlines erode as permafrost that once held them together disappears. The thaw of permafrost "
        "is a slow-motion geological event, but it is already reshaping the Arctic landscape and the lives of "
        "the communities that depend on frozen ground for infrastructure, food storage, and travel."
    ),
    (
        "Cherry blossom phenology in Japan has been recorded continuously for over a thousand years, making it "
        "one of the longest ecological time series in existence. The dates of first bloom and full bloom "
        "correlate strongly with February and March temperatures: warm springs bring early blooms, cold springs "
        "delay them. Analysis of historical records shows that bloom dates have shifted nearly two weeks earlier "
        "over the past century, tracking the warming that has occurred across East Asia. The cherry blossom "
        "is more than an aesthetic spectacle — it is a biological clock that measures the accumulated warmth "
        "of the season. Farmers historically used bloom dates to time planting, and the timing continues "
        "to carry cultural and agricultural significance that extends far beyond the flowers themselves."
    ),
    (
        "Kelp forests along the Pacific coast of North America are among the most structurally complex marine "
        "ecosystems on Earth. Giant kelp can grow half a meter per day under optimal conditions, forming canopies "
        "that extend from the seafloor to the surface. These canopies create a three-dimensional habitat used "
        "by hundreds of species. Sea otters, reintroduced after near-extinction by the fur trade, play a "
        "keystone role by preying on sea urchins that would otherwise overgraze the kelp. The system is "
        "sensitive to water temperature — El Niño events that warm the California coast can decimate kelp "
        "forests within a season. Recovery requires years of normal conditions, and the recovery trajectory "
        "depends on whether otter populations are healthy enough to keep urchin populations in check."
    ),
    (
        "Typhoon season in the western Pacific runs from June through November, with peak activity in August and "
        "September. The storms form over warm ocean water when surface temperatures exceed 26 degrees Celsius, "
        "drawing energy from evaporation. As a typhoon approaches a coastline, its storm surge can raise sea "
        "level by several meters, inundating low-lying areas that have been populated for centuries because "
        "of their fertile, flood-deposited soils. Traditional Japanese architecture developed roof designs "
        "and construction techniques specifically adapted to typhoon winds. The storms also bring enormous "
        "quantities of rain that recharge aquifers and flush nutrients into coastal waters, producing "
        "temporary surges in fishery productivity in the weeks following a storm's passage."
    ),
    (
        "Bamboo groves across East Asia flower synchronously at intervals of several decades, then die. "
        "The interval varies by species — some bamboo flower every 48 years, others every 120 years — but "
        "within a species, the timing is remarkably consistent across geographically separated populations. "
        "The evolutionary logic of mast seeding is thought to involve predator satiation: by producing seeds "
        "only rarely and in enormous quantities, the bamboo overwhelms the capacity of seed predators and "
        "ensures that some seeds survive to germinate. For the giant panda, which depends almost entirely "
        "on bamboo, these mass die-offs are ecological crises that have forced range shifts and, in the "
        "modern era of fragmented habitat, have contributed to population decline."
    ),
    (
        "The seasonal ice of the Sea of Okhotsk reaches its maximum extent in February, covering an area "
        "roughly the size of the Korean Peninsula with a mosaic of drift ice, pack ice, and polynyas — "
        "open water kept ice-free by wind and upwelling. This ice is not merely a physical feature; "
        "it is habitat. Steller's sea eagles overwinter on the ice, preying on fish in the polynyas. "
        "Seals haul out on ice floes to give birth. The ice edge is a zone of intense biological "
        "productivity, where nutrients stirred up from depth by convection support blooms of diatoms "
        "that are grazed by copepods, which in turn sustain fish and whales. The annual formation "
        "and retreat of this ice is a pulse that drives the ecology of the entire North Pacific."
    ),
    (
        "Soil formation is one of the slowest processes in terrestrial ecology, proceeding at rates "
        "of roughly a centimeter per century under favorable conditions. The process begins with "
        "the physical and chemical weathering of parent rock by frost, water, and acids produced "
        "by lichens and roots. As organic matter accumulates from dead plants and animals, the "
        "soil develops distinct horizons: a dark, humus-rich topsoil; a lighter subsoil where "
        "minerals have leached down; and a transitional zone above bedrock. Earthworms and other "
        "soil invertebrates mix these layers and create channels that allow water and air to "
        "penetrate. A square meter of healthy temperate soil contains billions of bacteria, "
        "millions of fungi, and thousands of invertebrates — an invisible ecosystem of enormous "
        "metabolic significance."
    ),
    (
        "El Niño events reorganize atmospheric and oceanic circulation across the Pacific on timescales "
        "of one to several years. During a strong El Niño, trade winds that normally pile warm water "
        "in the western Pacific weaken, allowing warm water to slosh eastward toward the Americas. "
        "The consequences are global: droughts in Australia and Indonesia, floods in Peru and Ecuador, "
        "disrupted monsoons across South Asia, altered hurricane tracks in the Atlantic. The event "
        "was named by Peruvian fishermen who noticed that the warm water arrived around Christmas. "
        "Modern monitoring systems can predict El Niño events months in advance, but the practical "
        "impact on agriculture, fisheries, and water supply continues to be enormous, particularly "
        "in tropical and subtropical countries with limited adaptive capacity."
    ),
    (
        "The spawning runs of Pacific salmon connect marine and freshwater ecosystems across the entire "
        "breadth of the North Pacific. Salmon spend two to seven years at sea, feeding on marine "
        "productivity and accumulating nutrients in their bodies. When they return to spawn and die "
        "in the streams where they hatched, they deliver a pulse of marine-derived nitrogen and "
        "phosphorus to river catchments that would otherwise be nutrient-poor. Bears, eagles, and "
        "wolves carry salmon carcasses into the forest, where they fertilize riparian vegetation. "
        "The rings of Sitka spruce trees near salmon streams record bumper years of spawning as "
        "wider growth rings, because the trees absorb nitrogen from decomposing fish. The salmon "
        "run is a river of marine nutrients flowing into the terrestrial ecosystem."
    ),
    (
        "Fog is a significant source of moisture in coastal ecosystems where summer rainfall is sparse. "
        "Coastal redwoods and the cedars of Chile's fog forests intercept fog droplets on their "
        "needles, which coalesce and drip to the ground at rates that can equal or exceed rainfall "
        "during dry months. The trees effectively act as precipitation collectors, expanding the "
        "hydrological budget of the ecosystem beyond what rain alone would support. Insects and "
        "lichens that live in the canopy have evolved to extract water from fog. The persistence "
        "of these fog forests depends on the maintenance of cold upwelling offshore — the same "
        "oceanographic conditions that support productive fisheries. Warm episodes associated "
        "with El Niño can suppress fog for entire seasons, stressing trees and shifting the "
        "composition of fog-dependent communities."
    ),
    (
        "Volcanic eruptions reset ecological succession across entire landscapes, burying previous "
        "vegetation under ash and lava and creating new substrate for colonization. The 1980 "
        "eruption of Mount St. Helens in Washington State provided ecologists with a rare "
        "opportunity to study primary succession in real time. Within months of the eruption, "
        "prairie lupines were establishing in the ash, fixing atmospheric nitrogen and beginning "
        "to build soil. Pocket gophers that survived underground burrowed through the ash and "
        "mixed buried topsoil to the surface. Within a decade, shrubs and young conifers had "
        "established in patches protected from wind erosion. The recovery was neither uniform "
        "nor predictable — it was a mosaic shaped by local topography, wind patterns, and "
        "the chance dispersal of seeds and spores."
    ),
    (
        "The deep ocean is the largest and least-explored habitat on Earth, a cold, dark world "
        "where pressure increases by one atmosphere for every ten meters of depth. At the abyssal "
        "plain, four to six kilometers below the surface, temperatures hover near freezing and "
        "food arrives as a slow rain of organic particles from the sunlit surface layer above. "
        "This marine snow sustains communities of sea cucumbers, brittle stars, and bacteria "
        "that have evolved extraordinary patience, growing and reproducing at rates orders of "
        "magnitude slower than their shallow-water counterparts. Hydrothermal vents interrupt "
        "this sparseness with oases of chemosynthetic productivity, supporting tube worms, "
        "clams, and shrimp that derive their energy from sulfur rather than sunlight. "
        "These communities exist in complete independence from solar energy — the only "
        "ecosystems on Earth that do."
    ),
]


def main():
    output_dir = Path("corpus/processed/environmental_time")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "test_corpus.jsonl"

    with open(out_path, "w", encoding="utf-8") as f:
        for i, text in enumerate(CHUNKS):
            record = {
                "text": text.strip(),
                "source": "synthetic_natural_history",
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "chunk_index": i,
                "parent_hash": f"synthetic_{i:03d}",
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Generated {len(CHUNKS)} chunks -> {out_path}")


if __name__ == "__main__":
    main()
