# What Once in a Runtime is about

A technical claim becomes more useful when we understand its conditions.

An algorithm can be faster for one workload and slower for another. An abstraction can simplify a design while adding a cost elsewhere. A convincing result can leave an important case untested.

Once in a Runtime is a place to explore those details through small experiments and technical explanations. I will follow questions across software, numerical methods, systems and other areas of engineering, using whichever tools help investigate them.

The aim is to understand where an idea holds, why it works and what changes the answer. An investigation can support the original claim, uncover a limitation or leave the question open.

When there are measurements, I will share the code, correctness checks, configurations and limits needed to inspect them. When a piece is an argument rather than an experiment, I will make that distinction clear.

The studies currently taking shape start with two trading-related questions: what happens when simulated option-price paths finish at different times inside a SIMD calculation, and how we should arrange the work when testing many versions of a trading rule against the same history. They give us concrete examples to follow from a straightforward C++ implementation through to the costs of making it more elaborate.

I'm Fabrizio Donati. My background is in simulation and numerical software, and this is a personal space to investigate ideas that make me curious.

Code and experiments: https://github.com/fabdonati/onceinaruntime
