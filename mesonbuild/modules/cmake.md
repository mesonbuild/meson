# CMake module - install(EXPORT)

Informazioni nell'issue upstream: https://github.com/mesonbuild/meson/issues/7632#issuecomment-703851031

È importante separare le informazioni relative a un progetto in diversi file:

- projectConfig: quasi vuoto. Viene riempito da @PACKAGE_INIT@, dichiara le dipendenze con `find_dependency()` e include projectTargets
- projectTargets: contiene un bel po' di roba. Prima di tutto contiene la lista dei target che sono stati esportati, e controlla che nessuno di essi sia già stato definito precedentemente. Dopodiché dichiara appunto i target esportati con `add_library(project UNKNOWN IMPORTED)` e ci definisce alcune proprietà che sono valide indipendentemente dalla build configuration, come `INTERFACE_INCLUDE_DIRECTORIES`, `INTERFACE_LINK_LIBRARIES` (ovvero le librerie dalle quali il mio project dipende), e `INTERFACE_COMPILE_OPTIONS`. Infine include i vari projectTargets-\<config\>
- projectTargets-\<config\>: questo è il file che finalmente fa qualcosa. Per ogni target definito in projectTargets, applica le proprietà relative alla config corrente con `IMPORTED_CONFIGURATIONS` e definisce dove i file degli IMPORTED targes si trovano su disco con `IMPORTED_LOCATION_<config>`

Come ho intenzione di implementare questo puttanaio? Bella domandina.

Procediamo per piccoli passi.

Dato che non sono un mago, voglio implementare 'sta roba solo per una singola dependency, e senza un sacco di quelle cose che CMake fa. Ad esempio, Meson non ha questo concetto di poter avere più configurazioni contemporaneamente, quindi andrò sicuramente a generare un solo projectTargets\<config\> dove \<config\> sarà la configurazione corrente. Il processo che mi immagino è tipo che passo la mia `project_dep` a `cmake.generate_package_export()` e questo guarda le proprietà della mia dep per configurare i vari file, in particolare mi aspetto che sia in grado di scrivere tutte le proprietà che posso passare a una chiamata a `declare_dependency()`. I `compile_args` andranno nel projectTargets-\<config\>, le `include_directories` nel projectTarget, i `link_args` nel projectTargets-\<config\>, `link_with` in projectTargets, e sto realizzando che forse usare una dependency non è il massimo... Non a caso `pkgconfig.generate()` usa una library. O forse ora che ci penso potrei usare davvero le dep... Boh, vediamo.

Ok, allora, tutto da capo.

- Il primo kwarg sarà `name`, il nome dell'export set, che se non specificato prende il nome del progetto. Questo perché un progetto potrebbe esportare più di una libreria, e farà anche da namespace.
- Avrò poi un kwarg `targets`, al quale passo le librerie da esportare.
- kwarg `extra_options` per passare flag extra da mettere in `target_compile_options(INTERFACE)` nel `projectTargets`

Ed ora la lista di cose da fare per ogni library:

- Uso il nome della libreria per popolare la lista di target in `projectTargets`
- Ottengo la lista delle dipendenze da `dependencies`, e per ognuna di esse mi prendo la lista di librerie e flag pubblici da `compile_args`, `link_args` e `link_with` per metterli in `INTERFACE_*`. Questa cosa va fatta ricorsivamente, perché ogni dependency può dipendere da altre dependency.

- projectConfig richiederà poche modifiche
