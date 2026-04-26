# Modellering av møtetildelingsproblem gjennom Mixed Integer Linear Programming

## Variabler

TODO: Endre slik at hele dokumentet tar hensyn til rom som en del av modelleringen.

`p`

- Person

`k`

- Komité

`t`

- Timeslot

`m(p, k, t)`

- Binær variabel
- Person `p` har møte med komité `k` i timeslot `t`

## Hjelpevariabler

`c(p, t)`

- Binære variabler
- Tidspunkt `t` passer for person `p`

`c(k, t)`

- Heltallsvariabel
- Kapasitet for komité `k` på tidspunkt `t` (hvor mange intervju de kan ha på det gitte tidspunktet)

`z(c, t)`

- Binær variabel
- Hvorvidt komite `c` har noen intervjuer på tidspunkt `t`.
- Lineariseres ved å ha følgende begrensninger:
  - `m(a, c, t, r) <= z(c, t)` for alle `c` og `t`.
  - `z(c, t) <= sum(m(a, c, t, r) for alle a og r)`.

## Begrensninger

For alle `p`:

- `m(p, k, t_1) + m(p, k, t_2) < 2` for alle gyldige `k, t_1` og `k, t_2`, hvor t_1 og t_2 overlapper eller er innenfor et gitt buffer-intervall.
- `m(p, k, t) <= 1` dersom
  - `p` har søkt på komité `k`
  - `c(p, t) => 1`
  - `c(k, t) => 1`
- `m(p, k, t) <= 0` ellers

For alle `k`:

- `sum(m(p, k, t)) <= c(k, t)` for alle personer `p` og tidspunkt `t`

## Rom
For å passe på at en komité får det samme rommet i påfølgende tider, vil vi ha at følgende ulikheter skal holde.


For å redusere antall variabler introduserer vi en binær hjelpevariabel `y(c, t, r)` som representerer at komite `c` har et intervju på rom `r` på tidspunkt `t` (med en eller annen søker).

For hver komité vil vi da ha:
- `y(c, t_1, r) == y(c, t_2, r)` men kun dersom
  - begge disse verdiene er 1 (altså at det er et intervju på )

TODO: Linke `y` til `m`.


## Mål

Maksimere `sum(m(p, k, t))` for alle `p`, `k` og `t`. Altså: Maksimere antall intervjuer som tildeles.

### Sekundærmål

- La intervjuene klumpe seg rundt klokken 12 og dermed også minske hvor mange hull komitéene får i sin intervjuplan.

## Nyttige ressurser

- https://python-mip.readthedocs.io/en/latest/quickstart.html
- https://towardsdatascience.com/mixed-integer-linear-programming-1-bc0ef201ee87
- https://towardsdatascience.com/mixed-integer-linear-programming-formal-definition-and-solution-space-6b3286d54892
- https://www.gurobi.com/resources/mixed-integer-programming-mip-a-primer-on-the-basics/
