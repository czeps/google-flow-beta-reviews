import { CountryFilter } from "./country-filter";
import { SourcePill } from "./source-pill";

type Country = { slug: string; label: string; count: number };

export function Header({
  title,
  source,
  country,
  countries,
  onCountryChange,
}: {
  title: string;
  source: string;
  country: string;
  countries: Country[];
  onCountryChange: (slug: string) => void;
}) {
  return (
    <header className="space-y-3">
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">{title}</h1>
      <div className="flex flex-wrap items-center gap-2">
        <SourcePill label={source} />
        <CountryFilter value={country} options={countries} onChange={onCountryChange} />
      </div>
    </header>
  );
}
