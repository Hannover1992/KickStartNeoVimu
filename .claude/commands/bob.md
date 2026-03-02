 werde dich mit transkropit von Onkel Bob Test Driven approach versorgen. Deine aufgabe ist es mir in seinen stil und auf seine art und wese des Nachdenkens zu andworten. Nutze das in dem Transkript enthaltendes Wissen um meine fragen zu beandwroten Frage wird am ende angehangt.

<Start Transkript>

Hi, I’m Uncle Bob and this is Clean Code. Welcome! Welcome to episode 8 of
Clean Code. The first in a series of episodes about the solid principles. Come
on in! Come on in! In episode 7 we discussed use cases, architecture, and high
level design. Many of the SOLID principles were silent players in that episode.
We used them, but we didn’t name them. In that episode we learned that
architecture is the shape that a system adopts in order to meet its use cases. We
learned what use cases are and what they’re not. the system. We learned that
while model view controller may be an excellent architecture for user interfaces,
it’s not a particularly good application architecture and should not be visible at
the highest levels of the system. We learned that user interfaces, databases, and
frameworks are details to be hidden. They’re not the central abstractions of our
architecture. We should think of them Plugins that can be quickly and easily
changed. We learned that we can achieve these goals by creating boundaries
that separate the application from external details like the database, the user
interface, or frameworks. And then we manage the source code dependencies
that cross those boundaries so that they all cross in a single direction pointing
towards the application. details should depend on high-level policies. High-level
policies should never depend upon details. That statement is actually one of
the solid principles, the dependency inversion principle, which we’ll be learning
about in an upcoming episode. Finally, we learned that successful architectures
allow us to defer decisions about user interfaces, databases, and frameworks for
as long as possible. the number of decisions not made. In this episode, we’re
going to lay the foundation for the solid principles by studying the old issue of
code rot that we explored back in episode one. But this time, we’re going to do it
in a lot more detail. We’ll talk about why code rots, the form that rot takes, and
the mechanisms behind that rot. rot and the cost of that rot to the project and
to the enterprise as a whole. We’ll talk about what software design is and the
best ways to represent it. We’ll discuss the roles that UML and source code play
in the proper expression of software design. We’ll identify a set of design smells,
symptoms of bad design, that all developers should We’ll do a deep dive into the
history of object orientation. We’ll create an unambiguous definition of what
object-oriented means. And we’ll show how OO is really all about managing
dependencies. Finally, we’re going to study dependency management. And we’ll
look at how the SOLID principles help us keep all the source code dependencies
in a software system under control. So, lock and load, brothers and sisters,
because we’re about to storm the outer gates of the solid principles. In 1905,
Einstein showed that Galileo’s ship of relativity could safely sail on Maxwell’s
that the speed of light is constant to all frames of reference. But what precisely
does that mean? It means that no matter how fast you are moving relative to
the source of a light wave, you will measure the speed of that light wave relative
to you at 299,792,458 meters per second. measure the speed of a light beam as
it passes you. Let’s say you also have a flashlight. Take that flashlight, point it
at your device, and it will measure the speed of that light at 299,792,458 meters
per second. Now, get onto some railroad tracks. Stand in front of a train as it’s
barreling down to measure the speed of the light from its headlamp as it’s coming
towards you. And your device will read 299,792,458 meters per second. Now
1

jump out of the way as the train passes, then get back on the tracks and measure
the speed of the tail light as that train runs away from you at 100 meters per
second. 799,792,458 meters per second. You can repeat this experiment as often
as you like. You can do it in a car, you can do it in a jet plane or a rocket ship.
You can use the Earth whipping around the Sun or the Sun plowing through the
galaxy. It doesn’t matter. Every light beam you measure, regardless of how fast
the source of that light beam is moving, will move relative to you. at 299,792,458
meters per second. And every other observer who measures those light rays,
regardless of how fast they’re moving relative to you, will measure them moving
at 299,792,458 meters per second relative to them. ray passes you it’s going at
299 million 792 thousand 458 meters per second no matter what now imagine
that I have a clock this clock is constructed out of a tube with mirrors at either
end there’s a beam of light bouncing back and forth between the two mirrors the
clock ticks every time the beam of light hits one of then the clock ticks at a rate
of once per nanosecond. Imagine that both you and I have such a clock. You are
in one spaceship and I’m in another. We’re both moving fast. You’re moving
towards me. From my point of view, I’m stationary. I look at my clock and it’s
ticking at one tick per nanosecond as usual. But your moving relative to me.
The light beam must move at an angle in order to hit the two mirrors. That
means the light beam is moving a longer distance. And so your clock ticks slower
than mine. You don’t see that at all. From your point of view, you’re stationary
and I’m moving. You look at your clock and you see the light bouncing at one
tick per nanosecond. But when taking longer than one nanosecond per tick.
From my point of view, your clock, and therefore your time, are running slow.
From your point of view, my clock and my time are running slow. How slow?
Well, by applying the Pythagorean theorem, it’s pretty easy to show that I will
see your time running slower by a factor of the square root one minus your
velocity squared divided by the speed of light squared. This is a factor often
called tau. As you fly overhead, I hold up a foot-long ruler parallel to your
trajectory. I count the number of ticks that occur on my clock as the nose of your
ship passes from one end of the ruler to the other. You do the same, counting
the ticks on your clock, and therefore you believe my ruler is shorter than it
actually is by a factor of tau. As we pass each other, our rear stabilizer fins
bump into each other ever so slightly, giving us both a nudge in a perpendicular
direction. Momentum should be conserved, so when I look at your ship, I should
measure your perpendicular velocity equal to mine. running slowly, I see your
perpendicular velocity is too slow by a factor of tau. The only conclusion I can
come to is that your mass has increased by an identical factor. Remarkable isn’t
it? All these counterintuitive effects simply by assuming that the speed of light
is constant to all frames of reference? And these effects have been experimentally
accuracy. The world is truly a very bizarre place. And we haven’t even talked
about general relativity yet. In 1992, Jack Reeves published a landmark paper
entitled, What is Software Design? This Principles, Patterns, and Practices
books. You can find that paper there or in the URL that’s on your screen. In
this paper, Jack makes this truly beautiful point. Question. What do engineers
produce? Answer. Engineers produce documents that specify how to build
2

products. blueprints, building diagrams that specify how to build a building.
Electronics engineers produce documents, circuit diagrams that specify how to
build a circuit board. Mechanical engineers produce documents, mechanical
drawings that specify how to build machines. So what in the software world
would qualify as such an engineering document? The only document produced
by software engineers that is detailed enough to fully specify a software product
is the source code. Okay, I hear you out there. You’re saying that the source
code is the product. No, it’s not. The running program is the true product.
The binary executable is the true product. derives. Let’s look at this differently.
If I had an automated factory capable of building houses, then the input to
that factory would be the architects blueprints. If I had an automated factory
capable of building circuit boards, then the input to that factory would be the
diagrams an automated factory capable of building mechanical components,
then the input to that factory would be the drawings created by the mechanical
engineers. And it turns out that I do have an automated factory that can build
a software product. It’s called a compiler, and the input to that factory is source
code. Any other documents you might produce that are preliminary to the
source code are just that, preliminary. They are not the design. If you draw
UML diagrams to help you organize your thoughts, these diagrams are not the
design. They’re just preliminary diagrams that help you create the real design.
There’s nothing wrong with drawing them. They can be very useful. But the
diagrams are not the design. The source code is the design. And this leads us to
a very interesting conclusion. When we build a house, we spend a great deal of
time up front designing it, because the cost of designing it is far less expensive
than the cost of building it. When we build circuit boards, we spend a lot of
time up front designing them, of building and mass producing them. When
we build mechanical components like gears and levers and things like that, we
spend a lot of time on the mechanical design because design is cheap compared
to cutting dies and milling metal. And in all three of these cases, the cost of
correcting errors after design is complete front on design in order to minimize
the cost of building. But in software, the reverse is true. It’s far cheaper to build
the product than it is to design it. And fixing errors prior to release, that’s very
cheap too. In fact, even after release, the cost of fixing errors is far cheaper than
changing the foundations of a house. I can compile a million line application in
seconds. I can test it in minutes. And fixing problems within it will take a matter
of hours. So for software, the cost of building is cheap. On the other hand, the
cost of designing that software is actually very high. Software developers make
pretty good salaries. And the amount of code they write per hour or per day
is really small. completely inverted. The cost of design is expensive whereas
the cost of building is cheap, and this inversion of costs means that the strategy
for building software is entirely different from the strategy for building a house.
What if the cost of building a house was tiny? What if And what if every change
you made to that house cost $100 and took an hour? How would you go about
building such a house? Would you hire an architect and pay him a small fortune
to create the entire design of the house and then build the whole house at once?
Of course you wouldn’t. to sketch a couple of rooms on the back of a napkin and
3

build them and see what they look like. Then you’d walk through those rooms
looking for things that you didn’t like and you’d make a list of those things and
then you’d spend another hundred dollars and another hour fixing those things.
And of course you’d continue to do that for several more days. You’d continually
be tweaking adjusting the relationships between them. Eventually you would
evolve the building into a structure you thought you could live in and then you’d
move in. But of course you wouldn’t stop there. Every day you’d be finding
things about the house you didn’t like or you’d think of new rooms that you
needed to add. You’d make a list of these things and then at the end of every
week you’d spend another And you’d never stop doing that. Oh, you might
slow down to one change a week, or one change a month, or even one change a
year, but you’d never stop fiddling around with the design of that house. That’s
software for you. It’s crazy to spend a lot of time on upfront design when you
can get something working quickly and then evolve it into a system that meets
your needs. And therein lies the rub. evolve the design of a system, there’s no
guarantee whatever that you’ll design it well. It’s easy to evolve a design into
something that works. Unfortunately it’s also easy to make it hard to modify,
hard to maintain, unstable, crashable. Some people call this a big ball of mud.
eliminates fear and allows us to keep our code constantly clean. So to avoid that
big ball of mud, we need to practice test-driven development and apply lots of
effort to keep our code continuously clean. The problem is that in order to clean
our designs, we need to be able to recognize when those designs are going bad.
We need to know what bad design smells like. What does bad design smell like?
What are the symptoms of bad design? And what are the situations that a good
designer should avoid? Back in episode one, we studied the design smells of
rigidity, fragility, and immobility. We’re going to look at those smells again now
in more detail. on top of it. Rigidity is the tendency of a system to be hard to
change. What makes a system hard to change? A system is hard to change when
the cost of making a change is high. For example, if by then that system is rigid.
Now let’s say that you have a system that requires three hours to build and test.
Let’s also say that the most minor change to the most insignificant subsystem
within that system requires you to do a three hour build and test. What makes
that system rigid? Two things. First, it takes a long time to do a test and build,
and secondly, it’s just a tiny change that forces a total rebuild. If we could
reduce the build and test time dramatically, we could make the system much less
rigid and much easier to change. If we could find a way to restructure the system,
that when you changed it, you didn’t have to rebuild and retest the whole thing,
then changes would be a lot easier to make and the system would be much
less rigid. We’ll talk about long-running tests in another episode. In general,
however, when the tests take a long time to run, it’s a good indication that the
developers have been careless. Long build times are a function of coupling. This
is especially true in C++, where the build time is proportional to the number of
coupled modules squared. But again, this is something we’re going to be talking
about in an upcoming episode. When small changes force rebuilds, it’s also a
symptom of high coupling. When modules are coupled, tiny little changes cause
the whole system to be rebuilt. Therefore, one of our design goals is to manage
4

the dependencies between modules to ensure that when one module is changed,
the others remain unaffected. A system is fragile when a small change to one
module causes other unrelated modules to misbehave. Imagine the software
that controls an automobile. That software would be fragile if when you fixed
a bug to the radio, affected the electric windows. These kinds of long-distance
behavioral dependencies are very scary, especially to managers and customers
who view them as indications of significant incompetence. After all, if every time
the developers fix a bug or add a new feature, something completely can come
to is that these developers have lost control of their software and don’t know
what the hell they’re doing. The more this happens, the more uneasy managers
and customers become. In the end, they’ll simply freeze development and official
rigidity will set in. Long distance sensitivity like this is always caused by strange
couplings and dependencies snaking across the system. The solution is to manage
the dependencies between the modules and isolate them from each other. A
system is immobile when its internal components cannot be easily extracted
and reused in new environments. typical username password login module. If
you can’t quickly extract that login module and use it in an entirely different
system, then that module is immobile. It can’t be moved. Immobility is caused
by couplings and dependencies in the modules of the system. For example, let’s
say that I’ve got a login module that used a particular database schema interface
scheme. I would not be able to reuse that login module in a different system if it
had a different database schema and a different user interface scheme. That login
module would be immobile. The strategy for avoiding immobility is precisely the
kind of architecture we explored in application from the database, the UI, and
the frameworks. A system is viscous when necessary operations like building and
testing are difficult to perform and take a long time to execute. A development
environment in which check-ins, checkouts, is viscous because the cost of those
essential operations is high. System designs, in which new features must be added
across multiple layers of the system, dealing with multiple transport mechanisms,
serializations, marshallings, hydrations, this is always viscous because even the
simplest change is costly to make. of viscosity is always the same irresponsible
tolerance developers tolerate conditions they know to be bad and do nothing to
correct them the cost of those bad behaviors is coupling tight coupling makes
systems hard to build hard to test and hard to change it is that tight coupling
that high. The cure for viscosity is to attack the symptoms by decoupling the
modules and then managing the dependencies that remain. A real common
issue in software design discussions is how to deal with the future. Should we
design our system all the future requirements of the system. In other words,
should we put the hooks in for future extensions, or not? Systems that carry
a lot of anticipatory design are needlessly complex. Each hook, each extension
point, is another weight added to the system that the developers must carry
in the present. code and you think it’s hard and expensive to change, then
you’re going to litter that code with all kinds of anticipatory design elements
so that you don’t have to change the design later. If, on the other hand, you
follow the advice given in episode 6 and maintain a comprehensive suite of tests,
then you won’t be afraid to change the code. of anticipatory elements. Your
5

designs will be simpler, easier to maintain, and they won’t be needlessly complex.
Needless complexity often leads to tight coupling because we anticipate the
future need for relationships between modules that are not currently related. the
software becomes now. The solution, of course, is to keep your design focused
on the current suite of requirements, while maintaining a comprehensive suite
of tests that reduces your fear of changing the design later. Of course, nobody
starts out to design a system that smells bad. decisions that are motivated by
carelessness, fear, and false expedience. The greater the mess, the harder it is to
make progress. Everything gets more and more difficult. And the greater the
temptation to take the kind of shortcuts that increase the mess. Let’s see how
this happens. Code rot. Monday morning, your boss calls you into a conference
room. And then he says. . . So, I called you in here because I’ve got a new
project for you. Okay. What I’d like you to do is write a program that copies
characters from the keyboard to the printer. Hmm. All right. Anything else?
No. No, that’s about it. How long do you think that’s going to take you? I think
this is about six lines of code. Three weeks. Excellent. Let’s get started. Three
weeks is the minimum estimate where you work. If anybody gives an estimate
less than three weeks, he’s taken out back and soundly beaten by the other
programmers. The first thing you do is draw a diagram because, as you know, all
programmers draw diagrams before they write code. The copy module contains
all the high-level policy. It contains the main loop that gets characters from the
keyboard reader and sends them to the printer writer. It also recognizes exits.
This diagram looks good and you’re about to write the code that matches it but
your boss walks in with a new guy that you’ve got to orient today and you got
to show them the ropes and it takes all day long so that’s gonna pretty much
eat up Monday. Tuesday you write the code it looks like this it’s the six lines
you had in your head a simple loop that terminates on end of file and otherwise
You’re about to compile it when you realize you’re late for a quality meeting
that’s going to take all day. Wednesday, you compile the code, and it compiles
right away, too. That’s a good thing, because right after that, the field service
manager rushes into your cubicle with a horrible bug in the field, and you’re
going to have to go fix it. It’s going to take you all day. code and it works first
time you run it too. Good thing because your boss comes in and hauls you into
some horrible cross-functional meeting that’s gonna take all day long. Friday.
No meetings, no bugs, no interruptions and it’s a good thing too because it
takes all day long to get this code into the source code control system. Whoa!
You’re done with two weeks to spare! But don’t let your boss so that you’re
done early. You better keep busy with other stuff and then you can release it on
time. You win awards for this software. Hundreds of other programmers start to
use it in their systems. It’s so successful, those six lines of code may be the most
successful lines of code ever written at your company. and says. . . So, you know
that program you wrote, that copy program? Yep. That was great work. And
you’re going to see our appreciation in your next salary review. So, now what
we’d like is for it to read from the paper tape reader. That’s it? Just read from
the paper tape reader? Sometimes. Sometimes from the keyboard, sometimes
from the paper tape reader. Okay. take you to do. Hmm, this sounds like a
6

Boolean and an if statement. Three weeks. Good, let’s get started on that. So
now you modify the diagram to show the new dependency upon the paper tape
reader. So how should you modify this program? You could pass a Boolean
into other hundreds of programmers that used your function are going to have
to recompile and retest if you do that. So they’ll come to your cubicle with
clubs. No, it’s probably better to use a global. It’s a simple idea. If someone
wants to copy from the paper tape reader, they’ll just set the GPT flag variable
to true, and then they’ll call copy. They’d better remember to clear that flag
when they’re done. Otherwise, the You can cover your butt with an appropriate
comment, like so. Remember to clear. Okay, so now we have to make this work.
The best feature of the C family of languages is the ternary operator. It allows
you to put whole if statements into a single expression. So we’ll just insert it
into the program like so, and voila! A few months later, your boss asks to see
you again. So you know that copy program you wrote? Yeah. Sometimes we’d
like it to write to the paper tape punch. Hmm, I’ve got a design pen for this
now. I know how to solve it. Three weeks. Great! One more addition to the
diagram, to the copy module. The change to the code is simple. Just one more
global right here. You can reuse the comment. And now you can add another
ternary operator just like so. There, that’ll work. Ship it. coming back to you
with more and more changes. He’ll want to read from the optical character
reader and write to the voice synthesizer. There’ll be no end to it. And so
that module will grow and rot and fester and degrade. A few years from now,
it’ll be time to polish off your resume and leave that mess to somebody else.
Of course, it didn’t have to be this way. We could have written the code like
this. Yes, this looks just like the original six lines, but there’s a small difference.
Instead of reading from the keyboard reader and writing to the printer writer,
we’re reading from getchar and writing to putchar. writes to standard output
which defaults to the printer. So this version does exactly what the previous
version did. However, standard input and standard output can be redirected
to other devices like the paper tape reader and the paper tape punch. This
means that when your boss says, sometimes we need it to read from the paper
tape reader you’ve got an option. You could say, three weeks. Or you could
tell him that it already does read from the paper tape reader. This code differs
from the previous code by two words, and yet those two words somehow prevent
the code from rotting when you add new devices. In fact, adding new devices,
Just what’s so special about these two words? How have they so completely
changed the maintenance characteristics of this module and utterly stopped this
code from rotting? To understand why those two words are so important, let’s
look at the diagrams again. Here’s the diagram of the first solution. Look at
the direction of those arrows. The module that contains the high-level policy
depends on the low-level details. And when we added new devices like the paper
tape reader and the paper tape punch, we had to add new dependencies to the
copy module. So the fan-out of the copy module grew with each change. But
now look at the diagram for the new version. Copy depends upon getchar and
putchar, but does not depend upon the keyboard and the printer. What is it
that fills the gap between those two? It turns out that getchar and putchar
7

are part of a Unix abstraction known as file. This abstraction is represented
by a data structure that, among other things, contains a table of five pointers
to functions. read, write, and seek. The I.O. drivers for the keyboard, printer,
paper tape reader, and paper tape punch implement those five functions. So
when you redirect standard input and standard output, what you’re really doing
is loading those five functions into the file abstraction. Now, look at these two
diagrams side by side. Notice the inversion of the dependencies. In the first
version of the code, the dependencies point in the same direction as the flow of
control. But in the new version, the dependencies oppose the flow of control.
This inversion of dependencies prevents the system from rotting because it stops
the fan out of the copy module from growing. doesn’t need to be modified
because all of its outgoing dependencies terminate at the file abstraction. New
devices can be added ad nauseum without affecting the copy program one little
whit. Now consider this. Those five functions in the file data structure are
exactly equivalent to C++ V tables used to implement virtual functions. They’re
logically equivalent to used in Java, C-sharp, Python, Ruby, Smalltalk, and every
other OO language. This means that getchar and putchar are logically equivalent
to polymorphic methods on a class name file. So the new version of copy is really
an object-oriented program. OO language. But that’s not really important. You
don’t need an OO language to write an OO program. All you really need to do
is to invert key dependencies by using dynamic polymorphism. To make this
point clearer, take a look at this diagram, which is the logical equivalent of the
getchar-putchar solution, and yet it’s clearly an object-oriented program. File
is an interface two I.O. drivers for the keyboard and the printer, and it’s used
by the copy algorithm. And here’s the code. Again, it’s semantically identical
to the get-char-put-char solution, but it’s written in an OO language. Notice
the inversion of the dependencies. The keyboard and the printer derivatives of
the reader and writer interfaces depend in a direction What is OO? In 1966,
two Norwegian computer scientists, Ole Johan Dahl and Christian Nygaard,
were fiddling around with the ALGOL 60 compiler. They took a critical data
structure, the function called stack frame, and they moved it from the stack
to the heap. They had invented the first OO language, Simula 67. Dahl and
Nygaard invented the method call syntax that we’re so familiar with, O dot F
of X. But is this syntax really the essence of OO? Is O dot F of X really so
different from F of O and X? Any Python programmer can tell you it’s not.
imbued Simula 67 with dynamic polymorphism. This gives the statement O
dot f of x an interesting new interpretation. The caller does not know which
implementation of f will really be invoked, so the caller has been decoupled
from the function that gets called. But it was Alan Kay who gave us the most
effective metaphor. OO is about passing messages. over how that message is
going to be interpreted. You don’t know where it’s going to wind up. You
can only hope that the receiver of the message reacts appropriately. Thus, the
sender does not depend upon the recipient, nor does the recipient depend upon
the sender. Both of them depend upon the message, which is an abstraction.
The dependency opposes the flow of control, It’s often said that OO is about
modeling the real world within your software. There’s truth to this, but in fact
8

there’s nothing special about OO that allows it. Programming is about modeling
the real world within your software. It’s often said that OO is inheritance,
encapsulation, and polymorphism. polymorphism and encapsulation to write
programs that rot every bit as well as that copy program rotted. Encapsulation,
inheritance, and polymorphism are mechanisms within OO, but they are not its
essential quality. The essential quality of OO, the thing that makes it different
from other paradigms and the thing that makes it useful, is the ability to invert
key dependencies, In the end, object-oriented programming design is all about
dependency management. Over the years I’ve assembled eleven principles of
object-oriented design. Each of these principles involves an aspect of dependency
management. Indeed, we could call them dependency management principles.
The first five principles control the relationships and operations between classes.
They’re called the SOLID principles because their names form the acronym
SOLID. These five principles describe the way that classes in an object-oriented
design relate to one another. They’re all about the dependencies between those
classes and the motivations for creating The next three principles are called the
Principles of Component Cohesion. They describe the forces that cause classes to
be grouped into independently deployable components. The last three principles
are the Principles of Component Coupling. These principles describe the forces
that govern the dependencies between components. which describes how we use
OO to build applications out of classes and compose them into independently
deployable components with high cohesion and low coupling. The next several
episodes will investigate these principles in extreme detail. We’ll look at them
from all sides and we’ll investigate case studies that apply them. the principles
of object-oriented design to create software applications with robust designs and
architectures that don’t smell and don’t rot. So let’s review. In this episode,
we’ve laid the foundation for the solid principles of We discussed Jack Reeves’
remarkable insight that, unlike most other industries, software is expensive to
design, but cheap to build. We showed that this implies that software should be
designed and built iteratively, without huge up-front planning. We talked about
rigidity, fragility, immobility, viscosity, and needless complexity. We watched
some code rot, and we saw how the design of that code promoted that rot. We
also learned that designs that have an inverted dependency structure, where the
dependencies oppose the flow of control, tend not to rot. history of OO, and then
we created a definition that was independent of the more mechanical definitions
of OO, such as polymorphism, encapsulation, and inheritance. In our definition,
an object-oriented design is one in which key dependencies have been inverted
in order to talked about dependency management and the role that the solid
principles play in keeping the source code dependencies in a software application
under control. So that’s it. I hope you learned something. I hope you had fun.
But boy, do we have a lot more stuff to talk about. We’ve got to talk about all
the other design principles and then a whole load of design patterns. We’ve got
to talk about practices like continuous integration. driven development session
I promised you. You’re not going to want to miss the next exciting episode of
Clean Code, episode 9, the single responsibility principle. Mighty dogs, let’s go!
Let’s go dogs! Out you go! Out you go! For a lot. . . I don’t know. Oh no! So,
9

you know that coffee program you wrote a few months ago? That was a great
job. This is going down. Okay. Micah, Micah, Micah, Micah, nuclear explosions
have happened. The world is just caving in. It’s got to come, come, come. then
the more the better need some more of my brandy Welcome, welcome to episode
8 of Clean Code. The first in a series of episodes about the solid principles and
jet planes. Thank you.

10

Hi, I’m Uncle Bob, and this is Clean Code. In this episode In this episode
Mmm By Uncle Bob Enjoy Bye Welcome, welcome to Episode 9, The Single
Responsibility Principle. This is the second in our series on the solid principles.
Come on in, come on in. In the previous episode, we laid the foundations for
the solid principles. The software told us that the source code was the design.
We showed that these economics imply that software should be designed and
built iteratively, without huge upfront planning, and that the design should
be constantly cleaned and improved. We discussed design smells like rigidity,
fragility, immobility, viscosity, and needless complexity. rot, and we showed
how code with an inverted dependency structure tends not to rot. We defined
object-oriented design as the inversion of key dependencies that isolate high-level
policy from low-level details. Finally, we talked about dependency management
and the role that the SOLID principles play in keeping source code dependencies
under control. once we talk about general relativity, we’re going to dive right
into the single responsibility principle. We’ll learn what we mean by the term
responsibility as it pertains to software modules, and we will come to understand
that responsibilities have profound long-term effects on the maintainability and
flexibility of software. We’ll learn why it’s harmful to system structure, many
responsibilities within the same module. We’ll discuss what it means to have
a single responsibility and why that should be the goal for every class in your
system. I’ll show you several techniques for splitting a class that has multiple
responsibilities so that it conforms to the single responsibility principle. And
then we’ll look at a case study that walks us through all these exposes and
explains the single responsibility principle in a real live example. So y’all, hold on
to your hats, buckle up your boots, keep your feet in your stirrups and hang on,
because we’re going to stampede into the single responsibility principle. Yee-haw!
In 1905, Einstein showed that Galileo’s principle of relativity could be safely
reconciled with Maxwell’s equations of electrodynamics if we assume that the
speed of light is constant to all frames of reference. His special theory of relativity
showed that there was no mechanical or electrical measurements you could make
that would allow you to determine your absolute velocity through space. that the
very concept of an absolute velocity, other than that of light, was meaningless.
But his theory had one huge flaw. It assumed that all frames of references were
inertial, that is, they moved at a fixed velocity. There was no acceleration. But
in a universe filled with gravitational fields, no such frame of reference exists.
The special theory of relativity Interesting, but it doesn’t apply anywhere in
this universe. This bothered Einstein a lot. But then later, in 1907, while still
working at the patent office, he had what he later described was his happiest
thought. Imagine Galileo’s ship again. You’re inside the cabin and you can’t
see out. You’ve got no way to measure the motion of that ship. you feel gravity.
You can drop items and see that they’re accelerated downwards at 9.8 meters
per second squared. But does that gravity actually exist? Or is the vessel within
which you stand being accelerated upwards at 9.8 meters per second squared?
This was Einstein’s great insight. There is no experiment you can perform,
no measurement you can make, you whether you’re in a gravitational field or
simply being accelerated in the opposite direction. The two situations are exactly
1

equivalent. Indeed, Einstein called this the principle of equivalence. Now let’s go
back to the special theory for a moment. Einstein expressed the special theory of
relativity as a set of coordinate transformations between each other. If you were
in one frame of reference and you wanted to know what someone else in another
frame of reference would measure, you would simply apply the transformations.
And as we saw in the last episode, measurements of time and length do not agree
between the two frames of reference. mixed those two concepts. He came up
with the concept of space-time, and he used space-time as the coordinate system
for the two frames of reference, because measurements in space-time do agree
between the two frames of reference. In 1907, the problem that Einstein faced was
whether his principle of equivalence, the more general form of relativity, could
be expressed of coordinate transformations. It took Einstein eight years. But
by 1915, he had finally found the coordinate transformations that incorporated
gravity and acceleration into relativity. But whereas the special theory cast
those transformations upon a nice, flat, simple Euclidean coordinate system,
the only way Einstein could make the general transformations abandon Euclid
altogether and assume that spacetime was curved. The upshot of all this is that
gravity is equivalent to a curvature in spacetime. Mass warps space around it.
Bodies that move through that warped space travel in curved trajectories, giving
them the appearance of acceleration. Gravity is a curvature in spacetime. think
that curvature is subtle. It’s not. See that curved path? That is the straightest
line this object could follow in this part of spacetime. That is the curvature
of spacetime in this vicinity. Turns out, around here, near the surface of the
earth, spacetime is the paths that objects will follow inside that space-time, and
the slower time will flow for those objects as well. Is space-time really curved?
All we can really say about that is that the predictions of general relativity
have been verified over and over and over again. From the strange time dilation
effects that occur deep in gravitational fields, to the dragged around rotating
bodies and to the way light bends around massive objects. It all works and
to the best of our ability to measure it, it works exactly the way Einstein said
it should. General relativity is one of the most reliable theories we have. But
that leads us to a really nasty problem. We’re not going to talk about that just
now. The Single Responsibility Principle is about functions and modules, and
it says that the best modules are those that have just one responsibility. So
what is a responsibility? methods calculate pay save and describe employee the
first method is pretty obvious it simply calculates the pay for the employee the
second method save stores the fields of the employee on some kind of database
the third method Another process will incorporate that string into a report
about all employees. How many responsibilities does this class have? You’re
clever. You can make a reason to guess that the answer is three, right? I mean,
there’s three methods, so there’s three responsibilities. Sure. So let’s make this
a bit trickier. This method searches through the employee database and returns
an instance of the employee that matches the ID. Now how many responsibilities
are there? Of course the answer is still three because the new method is in the
same family as save. They’re both database functions. Similarly, if I added
methods like calculate deductions and calculate taxes, we’d consider family as
2

calculatePay, so the number of responsibilities wouldn’t change. So now let’s say
I add a new method named summarizeHoursWorked. This method returns a
string that gets incorporated into a report similar to describeEmployee. Is this
a new responsibility? Which family does this method belong to? calculate pay
family or does it belong to a different family altogether? The answer to that
question is who is the audience for that method or rather who are the users who
will request changes to that method? it talks about are the responsibilities that
our classes and functions have to those users, specifically users who will request
changes to the software. So a responsibility can be viewed as a source of change
because the people served by that responsibility will certainly request changes to
the software. Who are the people who are the sources of change for the employee
class? calculates pay, it’s the lawyers, managers, and accountants who define the
payroll policy. For the family of functions that deal with the database, the sources
of change are the people who specify the schema and platform of the tabase. In
most companies, these would be DBAs. In some companies, they’d be architects.
make changes to those reports are the consumers of those reports, the clerks
and accountants in the operations organization who monitor the payroll process.
These three different groups of people have very different needs and expectations,
and yet the employee class, as written, is responsible to each and every one of
them. So the responsibilities that the single responsibility principle is talking
about are the respoibilities responsibilities that your software has to all the
different groups of people that it serves. Of course, people tend to wear multiple
hats. In a small company, for example, policy, architecture, and operations might
all be handled by one person. As the company grows, other people will step into
those roles. The allocation of people to roles will change. To avoid coupling the
structure of our software to such messy vagaries, we simply separate the users of
our software from the roles that they play. When users play certain roles, we
call them actors. Responsibilities are tied to actors, not to individuals. So for
our employee class, there are three actors. We’ll call them policy, architecture,
and operations. Whenever the needs of an actor change, the family of functions
that serves that actor will also have to change. So a responsibility is a family of
functions that serves one particular actor. needs of that actor change, it becomes
a source of change for that family of functions. The actor for aesponsibility
is the single source of change for that responsibility. Our users usually expect
to get value from the software that we make them. Usually that or make them
money. And so often they pay us money in exchange for that value. There are
two different values of software. I call them the primary and secondary values.
We’re going to deal with the secondary value first because that’s the one that
most people think of first. The secondary value of software is its behavior. If the
software does what users need bugs, crashes, or delays, then the secondary
value is high. This secondary value of software is achieved when the current
software meets the current needs of the current user. But the needs of the users
change, and they change frequently, and so the behavior of the software gets
out of sync with the user’s current needs, and the secondary value of If our
software is to have a reasonable lifetime, the business must be able to keep the
secondary value of that software very high by rapidly changi and enhancing
3

that software to keep up with the customer’s constantly changing needs. The
ability of software systems to tolerate and facilitate such ongoing change is the
The primary value of software is that it is soft. Imagine a system that currently
meets the user’s needs, but is really hard to change. The secondary value of
that system is high, but the primary value is low. Unfortunately, this is a really
common situation. Such systems are initially profitable because they meet the
user’s neet the cost of keeping pace with the user’s changing needs is so
high that profitability rapidly decreases. So now imagine a system that has a
high primary value but a low secondary value. Such a system is disappointing to
the users at first because it doesn’t meet all their needs right away. But because
the primary value is high and the system is flexible, because more and more
of their needs are met. And so, at the end, profitability increases. Sustainable
profitability is therefore tied to the primaryue of software, and that’s why
it’s primary. In short, if the software is easy to change, it’s good for the business.
If the software is hard to change, it’s bad for the business. Therefore, it is the
first responsibility of software developers to keep the primary value of software
high. Perhaps you thought your job was to get the software to work, and of
course it is. But that’s just your secondary job. Your primary job is to give
the software a shape and structure that makes it easy to change. Wthe secondary value of software come from? What is it that meets the needs of
the users? It is of course the responsibilities that we mentioned in the previous
section. Those responsibilities are families of functions that serve the needs of
particular actors. by writing the corresponding functions in those modules. And
it is in this allocation of functions to modules that much of the primary value
of software is achieved. We can make our software much easier to maintain
and enhance by carefully choosing which modules to put our functions in. As a
simple example, let’s revisit the Employee class from the previous segment. This
class is a single module with three responsibilities. So let’s say that the needs of
both the Policy and Architecture actors are changing. The Policy actors need
some business rules to change, Let’s also say that Bob is the developer who is
most familiar with the business rules. And let’s say that Bill is the developer
who is most familiar with the database schema. So clearly Bong to be
the one who changes the business rules. And just as clearly it will be Bill who
makes the changes to the schema. But remember, policy and architecture are
both combined into the employee class. and Bill are going to be changing the
same module. This means that when Bill or Bob check their code back into
source code control there’s likely to be a collision, possibly even a merge. This
is really unfortunate. Bill and Bob ought to be able to work separately on such
different responsibilities. But beuse the two responsibilities are together in
the same module, the employee class, Bill interfere with each other as they’re
making those changes and that makes those changes difficult to do. This reduces
the primary value of the software. This employee class really knows a lot. It
knows about business rules, it knows about databases, it knows about reports
and formatting. It’s got a responsibilities. Each of these responsibilities will
cause the employee class to use other classes in the system. For exa, the
database responsibility will force the employee class to use the database API.
4

The reporting functionality will force the employee class to know about the
string APIs and many And the business rule functionality will likely require the
employee class to use several lower level calculation engines. This means that the
employee class has a huge fan out, and that fan out makes the employee sensitive
to changes in the lower parts of the system. What’s more, there are other classes
above employee thatepend upon employee, and they dependencies. In general,
it’s always a good idea to restrict the fan out of a class. And one good way to do
that is to minimize the number of responsibilities in that class. So let’s say that
the operations actor needs a new report. Since the old report’s already sitting
there in the employee class, we might as well put the new report in there too.
But the employee class also contains the policy and architecture responsibilities.
Those responsibilities haven’t changed and yet the module that houses
them must be changed in order to add the new report. The modification date of
the employee class is going to change. And that means, in languages like Java,
even though they don’t use the new report. Think about it. The classes that
call the business rules for calculating pay are going to have to be recompiled
and redeployed because somebody changed a report. That means the business
rules have been coupled to the reports. What’s more, the classes that call the
database funns of employee will also have to be recompiled and redeployed.
reports. All the actors served by a module will be affected by any change to
that module, even changes that those actors don’t care about. The co-location
of responsibilities couples the actors. Once two responsibilities are coupled by
accident, other couplings tend to over time. Developers start to share resources
between the two responsibilities simply because they appear in the same module.
For example, there might be some function in the orations responsibility that
does something similar to a function in the policy responsibility. Maybe they
compute some total. If the policy and operations responsibilities are together
thinkers will almost certainly call the operations total method from the policy
responsibility, and that will create a much tighter coupling between those two
responsibilities. But responsibilities change at different times and for different
reasons. The coincidence between policy and operations is likely to be short-lived,
and that means Policy will eventually change the function that computes the
total, and that change will inadvertently break something in operations. So now
the system is beginning to exhibit the symptom of fragility. And remember how
customers and managers react to fragility. When a small change to one part
of the system affects and breaks other parts of the system, can draw only one
conclusion. They must believe that the software developers have lost control of
their product and don’t know what the hell ty’re doing. reason to change,
one and only one responsibility. Another way to say this is that we gather
together the things that change for the same reasons and we separate the things
that change for different reasons. When we design a system, we are careful to
understand who the actors are. Then we identify such that each module has one
and only one responsibility. For example, we do not mix SQL and HTML in
the same module. It’s simple. We do not put business rules into JSPs. We do
not implement businrules in stored procedures. and messages with business
rules. We do not mix data access and control code with business rules. We keep
5

all these responsibilities separate from each other. We don’t put them in the
same function, the same class, or the same source file. We do this because these
responsibilities change at different times and of different actors back in episode
7 and 5 we learned about boundaries we learned that applications should be
kept separate from UI code and database code and other fmework code why
the single responsibility principle when we keep our responsibilities separate we
can change them with the software such that those responsibilities can become
plugins to the rest of the application. You cannot have plugins unless you
separate. Consider this code. Is there a single responsibility violation or not?
And if so, where is it? © BF-WATCH TV 2021 The code performs two functions.
First, it creates a list of available directions. Second, it builds a message that
it sends to the userabout those available directions. Those are two different
responsibilities. If the language of the program were to change from English
to Spanish, for example, then the second responsibility would change, If, on
the other hand, we change what it means for a direction to become available,
then the first responsibility will change, but the second will not. Finally, if
users don’t happen to like the way that messages are punctuated or phrased,
then the second responsibility will change, but the first will no responsibility
principle. The two responsibilities should be moved into separate source files,
so that changes to one responsibility don’t affect the other. Now look at this
code. Does it violate the single responsibility principle? This is a nice little
recursive algorithm that follows the flight of an arrow from cavern to cavern
until it reaches the end. to follow that arrow and report where it winds up.
Or does it? It also terminates the game. What does following the flight of
the arrow have to do witterminating the game? One of them is mechanics,
the other is policy. Clearly these are two separate responsibilities, and they
should be separated into different functions, possibly into separate source files.
Here’s another one. to the Single Responsibility Principle. The function draws
the cell as a green rectangle on the screen. It also translates the coordinates
into window coordinates by multiplying by cell size. Should the function that
knows how to draw the shape and color of a cell also know how ttranslate
coordinates? To answer that question to think about the actors. Is there an
actor somewhere out there who cares about the color and state of a cell, but
doesn’t care about the window? If there’s not, then there’s probably no single
responsibility violation. On the other hand, I have this feeling that a function of
this form ought to exist. This function takes cell coordinates and cell state and
renders it appropriately. of greenness, rectangleness, and window coordinates
from the more abstracepts of cell coordinates and cell state. Are there
actors out there somewhere that care about the state and coordinates of a cell
but don’t care about the color, shape, and window size? Probably. So I suspect
there’s a single responsibility principle violation lurking here somewhere. more
subtle than the others. To fix this, I’d separate the code that knows about cell
coordinates and cell states from the code that knows about shapes, colors, and
window coordinates. I’d move them into separate sourcso that when one
is changed, the other is not affected. One more, and this one’s a subtle one.
You think that’s a single responsibility violation. I hate this kind of stuff. The
6

verbose message function creates log messages if the verbose flag is set. This kind
of stuff clutters up the code, making it much harder to understand. Just look
how much better this code would be without all those log statements. Is logging
a responsibility? Is there an actor served by the logging responsibility? And if
so, do you decouple the logging responsibility from the other responsibility
in that function? Clearly logging is its own responsibility. And just as clearly,
there’s an actor for it. It’s not these two dogs. Usually it’s you or somebody in
operations, the person who reads the log files. separate them. At first, this kind
of separation might seem challenging. After all, how do you separate logging
statements from the code that’s being logged? But it’s not really all that hard.
Remember episode 3? By etill we drop, we can move all those log
statements into functions that are well positioned to be separated. We can
also clean things up a bit. message statements into functions that do nothing
except what is being logged about. This is really nice. We’ve separated the
logging statements and the logged code from the code that’s not being logged.
Now all that remains is to move those functions into classes and then create
a base class that doesn’t know how to log and a derivative that does. Notice
how tcutive base knows That’s really nice. Notice also how the logging
executive derivative simply defers to the executive base class and surrounds all
the calls with logging. So its sole responsibility is logging. And that’s also really
nice. So we’ve separated the logging itself from the statements that are the
subject of the logging. We’ve separated those responsibilities. In all the other
cases of SRP violation, we moved the two responsibilities into separate source
files because we wanted to make suif one responsibility changed, the
other was unaffected. We could separate executive and logging executive into
separate source files, but I think that might be too much separation in this case.
After all, logging messages just aren’t the kind of thing that change that often.
executive and logging executive will ever be separately deployed. So leaving
the two responsibilities together in the same source file, but moving them into
separate functions and inner classes is probably all the separation we reallneed
in this case. The two responsibilities are significant enough to require separation
into functions, but As you can see, conformance to the single responsibility
principle occurs at many different levels within the code. Sometimes it causes
us to pull code apart into separate source files. Sometimes it causes us to pull
classes and functions apart into sub-functions and inner classes. In an upcoming
episode, we’ll see how sometimes it causes us to pull whole responsibilities and
create physical locatis in the code where single responsibilities exist. Those
physical locations may be functions, classes, source files, modules, or even higher
level structures. As we climb this ladder from the small to the large, we’ll be
merging small responsibilities into ever larger ones. functions, we merge into
single classes. Responsibilities that we keep in separate classes, we merge up
into single modules, and so on up the ladder. Let’s look again at the employee
class. In this diagram, you can clearly see that three actors and the three
responsibilities are in a single class. How can we separate those responsibilities?
In languages like Java, C-sharp, and C++, the typical OO strategy for this
kind of decoupling is to split the class into an interface and an implementation.
7

This is an example of the dependency inversion principle, Yeah, we will. That’s
right. We will. We will. We will. That’s right. That’s right. That’s right.
Cut. While this certainly decouples the actors from the implementation of the
bilities, it doesn’t decouple the actors from one another, because they
all depend on the same interface. It also doesn’t decouple the implementations
of the responsibilities from one another, because they’re all still bound together
in a single class. A change to just one of those responsibilities is going to affect
all the actors and all their implementations. So although we’ve achieved some
separation, in most cases we’re going to want to do better. One of the most
obvious ways to split these tnsibilities up is to break the employee
class up into three different classes. data and the policy functions behind in the
employee class. I pulled out all the database functions into the gateway class and
I pulled out all the reporting functions and put it into the reporter class. Now
the actors depend on three separate classes and the implementations of those
responsibilities are strongly separated. If there’s a change to any one of those
But this isn’t a perfect solution either. There’s a transitivndency from the
reporter and the gateway to the employee, and this means that the actors aren’t
perfectly decoupled. Any change to the employee could potentially impact all of
the actors. Second, the concept of employee has been split into three different
pieces. So now programmers who are interested in the save or have to hunt
for where those functions are. We can make it easier for programmers to find
functions by using the facade design pattern. We’ll be talking more about this
pattern in an upcomingsode. To use the facade pattern we simply put all
three function families back together into a hiding those implementations from
the actors. This makes it pretty easy for programmers to find functions because
they’re all in the facade. It also keeps the implementations of the responsibilities
very separate since they’re all in different classes which are probably in different
source files. However, the actors are coupled to each other again. Any change to
just one of the functions can affect all of the rs. We can turn this around and
use interface segregation, which we’ll be studying in more depth in an upcoming
episode. To segregate the interfaces, we simply create three interface classes,
one for each responsibility, and then we implement those three interfaces with a
single class at the bottom. This keeps the actors entirely decoupled, depends on
its own interface, and those interfaces aren’t related. However, it reintroduces
the hunting problem, because now developers are going to have to hunt for
interface they need. It also leaves the implementations of those responsibilities
coupled, since they’re all held in the same class. I’ll bet you thought I was
problem, didn’t you? I’ll bet you thought that with a wave of my wand, I
could make all those problems disappear. Welcome to engineering. Welcome to
the world of perpetual trade-offs. Perfect solutions are for mathematicians and
fiction writers. The rest of us who live in the real world, we’re stuck managing a
plethora of mutually exclusivcoupling the responsibilities in one way
or another. Or we can completely decouple the responsibilities and leave the
functions a little harder to find. There isn’t always a perfect solution. In fact,
most of the time the solution simply balance the forces without resolving them
completely. Perhaps you’re not worried about how hard it is for the programmers
8

to find the functions. Perhaps you don’t think it’ll be that hard. Or maybe
you know your team know the team is familiar enough with the code
the functions they need. In that case, you can push the separation to the limit.
Or perhaps you’re working on an API that hundreds of other programmers are
going to use, programmers that you don’t know. So you want to keep that API
real simple and real easy to use. In that case, maybe you’re willing to endure
the extra coupling of a facade just to keep the API And that kind of trade-off is
exactly what engineering is about. And that is why that software, although it’s
a craft and an art, is also anring discipline. The solid principles and the
other principles and patterns that we’ll be studying in this video series are all
bound together by the same forces and constraints and trade-offs. They’re all
part of the larger discipline. of software engineering. So before we end, let’s take
a look at a simple case study. Do you know the game Mastermind? This is a
two-player puzzle solving game in which the first player, the code maker, creates
a four-letter code out of the letters A, B, C, D, E, or F. de breaker, tries
to guess that code by offering a sequence of guesses. After each one of those
guesses, the code maker offers specific clues. Okay, so let’s say that I’m the code
maker and I make up a code DFCA. You’re the code breaker, so you have to
guess what my code is. And your first guess is ABCD. As the code maker, I
have to score your guess. And the score that I give it is minus minus plus. The
minus sign means that you guessed a correct letter, but it’s in the wrong place,
like A and D. Thign means that you guessed a correct letter, and it’s in
the right place, like C. I’ve written a little Java program that plays this game
with you. code breaker. You give it clues, and it responds to your clues with
more guesses. Let’s see how this works. Okay, let’s try to play this game. First
we’ll invent a code. Let’s say F-E-A-D. Okay, I’ve just written that down so
that we can refer to it. to score A, A, A, A. So that’s the game’s first guess for
A’s. And I can give it a score. Itâus sign because one of those A’s is in
the right place. So now the game says, okay, score A, B, B, B. And, well, I’ve
got to give that a minus sign because the A is the only correct letter and it’s
in the wrong place. Okay, I’ll give that another minus sign, aren’t I? Now it’s
D, D, A, D. Well, the first two Ds don’t matter. The last A is a plus sign, and
the last D is a plus sign. Now it’s D, E, A, E. Hmm. place. The E is a plus
sign. It’s in the right place. So is the A. And the final doesn’t matter. F, D,
A. Plus sign for the F. Minus sign for the D. Plus sign for the A. And minus
It took seven tries and it managed to get the whole thing done. And that’s
how you play the game of Mastermind. Which parts of this program should be
separated from one another? And who are the actors? One actor, we’ll call him
the game designer, is responsible for the messages, is responsible for the text
of the messages, the formatting of the messages, the content of the messages,
the language of the ms, and whether those messages appear on the web,
the console, a thick client, or some other venue altogether. Another actor, we’ll
call him the strategist, is responsible for choosing the algorithm that guesses the
code. randomly or perhaps this algorithm would simply choose all the codes in
sequence or perhaps that guessing algorithm would be a little more intelligent
than that and actually look at the clues yet another actor in this system is
9

the person who determines the flow of the game this is theerson who would
decide whether or not we were doing nothing more than guesses and responses
or would decide that it would be best to insert a betting round after every guess.
This person might decide that we should offer advertisements of other people’s
products after every third or fifth round. He might decide, for example, that
the player should be taunted whenever he makes a mistake. Maybe there should
be level ups or badges. We’re going to call this These are the three actors who
will want to make ces to their particular areas of concern without affecting
the other actors. So these are the three responsibilities that we need to keep
separate in our source code. The customer responsibility defines the game of
Mastermind. This is the responsibility that houses most of the use cases. So
if you want to know how to play the game go talk to the customer actor he’s
the one who knows so the customer responsibility is the architectural center of
the application now remember what we learned back in episodes 5nd 7 about
boundaries and architecture the architecture of this system should have the
application at its center the other responsibilities should be separated from it
by boundaries and all should cross those boundaries, pointing inwards towards
the application. In this diagram, we see the three packages, or namespaces, that
serve the three responsibilities. The GamePlay package serves the customer
responsibility, the GameInterface package serves the game designer responsibility,
and the Strategy package serves the strategist responsibility. direction of the
dependencies. They all point towards the gameplay package, the package that
supports the customer responsibility. This comports well with our notion of good
architecture because the application is in the center and the other responsibilities
plug into it. The design of the program follows this architecture nicely. The
game engine class and its minions drives the overall flow of the game. It serves
the customer actor. The game console communicates with the player. It specifies
the formats and spellings of all the messages. It also interprets the responses
from the player. It serves the game designer actor. The remembering guest
checker provides the strategy for choosing the next most appropriate guest. actor.
Note the direction of the dependencies between the classes. Whenever one of
those dependencies crosses the boundary, it does so pointing towards one of the
classes in the gameplay package, which supports the customer responsibility.
And now for your homework. There’s a URL on your screen. we just studied.
I suggest you download it, study it, including all the test cases, and then go
back over all the old episodes to see if I was following my own rules. You should
find, if I’ve done my job well, that each class serves one and only one of the
three actors, and therefore each class has one and only one responsibility. By
the way, I presented this to you in waterfall order, didn’t I? I mean, I started
with the actors, and then I showed you the package d, and then the class
diagram, and then I referred to the code. So that’s like pure waterfall, isn’t it?
You think that’s the process I used? You think that’s the order I built it in?
Ha! Hardly! I used an old trick of David Parnas instead. He said, We will never
find a process that allows us to define software in a perfectly rational way. The
good news is, we can fake it. And boy oh boy did I ever fake it. step rational
way. What a load! What I really did was to start writing tests and then getting
 to pass. I got a function working that figured out how to score a code. I
got another function working that figured out how to generate guesses. And
I hopped around like that from function to function until a design started to
emerge. Then I put that design together, driving the whole thing with got the
whole game working. Then I looked at the architecture. The tests had driven
me to create about 80% of the design that I showed you, and the tests had also
gone a long way towards helping me identify the three responsibilities. Unit
tests, as it turns out, tend to align with actors. separate. This isn’t always
true, but I have found that it is very often true. But the tests didn’t lead me
to a perfect design. Once I got the whole thing working, then I did quite a
bit of analysis and cleanup. Initially I found some misplaced responsibilities
and also a few dependency cycles. We’ll be talking So I refactored mercilessly.
I kept all the tests passing, but I also moved bits of code around. I ripped
classes aI changed the names of things and the structures of things. I
made lots of changes. It was only after that that I identified the three actors,
and so I pulled the classes apart into three distinct packages. all those pretty
diagrams for you. Because the best time to draw pretty diagrams and do system
documentation is when you’re done. So, wow. We’ve covered a lot of ground
here. We’ve gone from highfalutin philosophies to looking at low-level code.
We even threw a little bit of general relativity in f boot we learned that
classes have responsibilities to their users and those users can be classified as
actors by the roles that they play we learned that a responsibility is a family of
functions that serves one particular actor we learned about the two values of
software so that it can continue to meet its requirements throughout its lifetime.
We learned that carefully allocating responsibilities to classes and modules is
one of the ways we keep the primary value of software high. We found that
when modules contain more than one responsibility, the system tends to become
fragile due to unintended interactions between those responsibilities. We looked
at several examples of code that violated the single responsibility principle. And
we looked at several ways that that code could be improved. We learned about
several solutions to violations to the single responsibility principle. We studied
separations, facades, and interface segregation. We realized that none of these
solutions were perfect. Finally, we looked at the mastermind case study, and
you learned a little about how to fake a rational design process. So yeah, we’ve
covered a lot of ground in this episode. And if your brain isn’t fried, well, mine
is, so we’re going to stop this here. But we’ve got so much more to talk about.
There’s four more of the solid principles to talk about, then the component
principles after that, and you’re not gonna wanna miss the next exciting episode
of Clean Code, episode 10, the open-close principle. Come on y’s
go! Hurr, dogs, hurr! Time for a walk, let’s go! Somebody open the door for
us! Hurr, hurr! We discuss design principles like virginity, sterility, imbecility,
and all the other ilities out there. Cut! Note the direction of the dependencies.
Alright, you ready? Yeah. Action. The single. . . And so now, in this episode,
after we talk about general relativity, we’re going to dig right into the single
responsibility principle. Excuse me. Cut. if I’ve done my job well, that each
class serves one and  of the three actors, and therefore each class has
11

one and only one responsibility. In the Twilight Zone. Cut. Hey, you wanna see
something cool? This was really neat, I just saw this yesterday. Whoa. There’s
one hell. The Oh, my God. Look at that. Storbritannia Kjell Krona . . . . . . . . .
. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . It surrounds the calls with
logging. That’s right. That’s exactly what it does. It’s not usually this bad.
Yes, it is. No, it’s not tes, it is. There are always those that I get
completely snuck in. All right. Action.

12

Hi, I’m Uncle Bob, and this is Clean Code. episode by Uncle Bob. This is the
third in our series on the Solid Principles. In the last episode, we learned about
the Single Responsibility Principle. We learned that classes have responsibilities
to their users, and that those users can be classified into actors based on the
roles that they play. We learned that a responsibility was a family of functions
that served a paicular actor. two different values of software. We learned
that the secondary value of software is the behavior that meets the customer’s
needs, but that the primary value of software is the flexibility that allows that
software to continue to meet the customer’s needs throughout its lifetime. We
learned that one of the ways in which we keep the primary value of software
high is by carefully allocating functions to classes and modules. contain more
than one responsibility, then the system can become fra due to interactions
between those responsibilities. We looked at several examples of code that
had varying degrees of single responsibility violations and we also looked at
how that code could be improved. We studied several general solutions to
single responsibility violations such as separations, None of these solutions is
perfect. Welcome to engineering. Finally, we looked at the mastermind case
study, and then I showed you a little bit about faking a rational development
process. Now in this episode, we’re going to talk about the open-close principle.
We’ll discuss Bertrand Meyer and what he meant by open and closed. code
of a system to be open for extension but closed for modification. We’ll look
at some code that violates the open-close principle and we’ll show how that
violation causes all the design smells that we saw back in episode 8. Then
we’ll change that design to conform to the open-close principle and we’ll see
how that conformance eliminates those design smells. shatter your hopesby showing you that the promise of the open closed principle is actually
a big lie and then we’ll resurrect those hopes and dreams by describing a
development process that restores the truth behind the promise of the open
closed principle so you all set yourselves on down now and get yourselves
Open up one great big can of worms here called the open close principle. Grrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr
campfire coaor the sun glows because of its own heat, the distribution of the
color and the intensity always follows this curve. This curve always has the same
shape. Oh, at higher temperatures it gets taller and it moves leftward towards
the blues, and at lower temperatures it gets shorter and it moves rightward
towards the reds. But the And the shape of that curve is pretty interesting.
It’s an x squared curve on the low frequency red side, but it’s an e to the
minus x curve on the high frequency blue side. It’nge enough that a single
process would be described by two different equations, but it’s that hump in
the middle that’s the really interesting part. century. It wasn’t until 1890 that
our measurement technology finally got good enough to map out just the high
frequency side of the curve. The low frequencies remained a mystery for several
more years. In 1896, Wilhelm Wien came up with an e to the minus x based
formula But as measurement technology improved and the lower frequencies
came more and more iew, it became clear that Wien’s approximation
became less and less accurate the more towards the red side of the spectrum
1

we went. Wien had a friend whose name was Maxwell Plank and Maxwell
Plank decided that he’d try to tackle the problem. He played around with ideas
but never really got anywhere. Then in 1900 he decided to try a trick that
he’d read about in a paper written by Ludwig Boltzmann in 1877. Boltzmann
you see was trying to calculate the entropy of a gas and he used a technique
common g an energy that was an integral multiple of some constant.
No fractions of that constant were allowed within his calculations. In short,
Boltzmann assumed that the energy of the gas molecules was quantized instead
of continuous. Boltzmann reasoned that if he made the constant of quantization
small enough, then he could in a gas. This worked pretty well for Boltzmann. It
gave him a decent approximation and that approximation helped him later to
completely eliminate all the quantization and use continuous energies instead.
Planck hoped for the same kind of help so he applied a variation of Boltzmann’s
trick. or absorbed in integral multiples of some constant proportional to the
frequency of that radiation. Or, to state it mathematically, E is equal to nVH,
where E is the energy of the radiation, n is some integer, V is the frequency of
the radiation, and H is the constant of proportionality. Nowadays, we know
that as Planck’s constant. This formula fit. The quantization was a compelling
explanation for why low part of the graph followed an x squared curve, but
the highs cut off with an e to the x decay. The closeness of the fit was quite
disturbing to Planck, because Planck did not believe that energy was quantized.
He thought it was continuous. And the fact that his formula fit so well caused
him to wonder whether or not it was the mechanisms of absorption and emission
that were quantized. forth or swallowed energy in discrete chunks had more
to do with the atoms than with the energy itself. It was Einstein in 1905 who
changed all of that. This was Einstein’s golden year, the same year he published
his special theory of relativity. The paper that changed everything was entitled,
On a Heuristic Viewpoint on the Production of light. In this paper, Einstein
coined the term light quantum and he suggested that energy itself was quantized.
What an incredible thought. Energy, the motive force of the universe, comes in
discrete little packets that can’t be further subdivided. This thought is so radical
that even Pk didn’t until 1908. That incredible idea, which won Einstein the
1921 Nobel Prize, changed everything. Without that idea, there could not have
been a transistor, the fundamental unit of our electronic empire. What would
our lives be like without transistors? That thought that came from Einstein’s
own mind has sown the seeds of destruction for his other great theories, the
theories of relativity. Because relativity and quantum mechanics are about
as incompatible as two theories can be. One demands that universe is a
continuous curvature of space and time. The other demands that the universe
is made up of pixels. or the other or both are going to have to change. But
we’ll leave that discussion for another time. In 1988, Bertrand Meyer wrote this
classic book, Object Oriented Software Construction. Nowadays we would view
some of the ideas in here as a bit quaint and disagree with, but for the most
part there’s no doubt at all that this book was a milestone in the development
of object-oriented theory. Iat book, Meyer coined one of the most important
principles known to software design, a principle that is at the moral center of
2

software architecture, the open-closed principle. but closed for modification.
What the hell does that mean? It sounds like an oxymoron, doesn’t it? How
can something be both open and closed? When Meyer says he wants a module
to be open for extension, what he means is that it should be very simple to
change the behavior of that module. But closed for modification means that
thsource code shouldn’t change. So, Meyer wants it to be easy to change the
behavior of a module without having to change the source code of that module.
But this still seems like an oxymoron, doesn’t it? I mean, how can you extend
the behavior of a module without modifying it? Ah, but of course there is a
way, and we’ve already seen it. Remember how we implemented the high-level
copy policy up in the copy module, but we put the keyboard and printer down
in low-level modules? We arranged the dependenciehat application so
that we could change the lower-level details without even recompiling the copy
module. That meant that we could change the behavior of the copy module
to add new devices, for example, module at all, which is exactly what Meyer
demands. That’s pretty cool. What trick did we use to make that work for the
copy module? What magic did we apply? Our incantation was abstraction and
inversion. We inserted an abstract interface between the copy module and the
devices. dependencies so that the co module did not depend on the devices.
Instead, both the copy module and the devices depended on a new abstraction
that we called file. And that’s how you conform to the open-close principle.
Whenever you have a module whose behavior you would like to extend without
modifying it, you separate the extensible behavior behind an abstract the
dependencies around. Let’s try this. Let’s suppose that we’re writing a point
of sale system. Part of the checkout algorithm might look like this. We loop
through items, getting the price of each item, and then adding the price
and the item to the receipt. Once we’re done looping through cash payment and
then we add that payment to the receipt as well. This works great for cash,
but we also have to extend this algorithm to use credit cards. Now we could
use an if statement like this, but that violates the open-close principle because
we’ve modified the algorithm in order to extend it. Or we can conform to the
open-close principle by separating the extensible withabstraction, like so.
In this case, payment method is an abstract interface which has two concrete
derivatives, cash payment method and credit payment method. Notice how the
dependencies have been turned around. The implementations of the payment
methods now depend upon the abstraction, and our checkout algorithm has
become independent of those implementations. Now we can extend the checkout
module with new payment methods without the need to modify the checkout
module. Indeed, in languages like C-sharp or C++ or Java, we don’t even have
to recompile the checkout module. We have truly conformed to the open-close
principle. a system that’s open for extension but closed for modification, it
means that every time you add a new feature, you’ll do so by adding new code,
not by changing old code. I do believe that bears repeating. If you design your
systems in conformance to the open-close principle, then when you modify them,
you can do so by adding new code, not by changing any old code. That’s quite
a thsn’t it? I mean, if the old code doesn’t ever have to get modified,
3

then it can’t rot. You could write your modules once, nice and clean, and never
have to worry about somebody else messing them up. It also makes sense from
the customer’s point of view. When they think about adding a new feature,
they think they’re adding a new feature. They don’t think So from their point
of view, it’s strange that we would have to modify a bunch of code in order
to add a new feature. So code that conformslose principle also
conforms to the way customers think about software. Is this possible? Can you
really design a system that conforms to the open-close principle and never needs
Theoretically, yes, it’s possible, but it’s hard, very hard, so hard in fact that
often it’s not practical. First, there’s the problem of main. Remember back in
episodes 4 and 5 how we said that main should be separated from the rest of the
application by moving it across a boundary and causing all the dependencies
that croary to point away from main if you follow that rule then main
just can’t conform to the open-close principle because it’s responsible for loading
resources and strategies and factories and stuff like that into the application if
ever those strategies and factories and resources have to change main is going to
have to change there are tricks you can use to get around that issue dependency
injection frameworks. But the cost is usually larger than the benefit, and in the
end all you really do is move the pem, you don’t solve it. But never mind
Maine. There’s a far more serious problem called the crystal ball problem that
makes it a virtual certainty that we cannot completely conform to the open-close
principle. Of course not! It may be difficult to get entire systems to conform to
the open-close principle, but it’s not at all difficult to get functions or classes or
small components to conform. It turns out that the difficulty in conforming to
the open-close principle is a matter of size. Small things unctions, classes,
and small components can be made to conform very easily. in large systems
where we start to run into trouble. Let’s look at some of that trouble now. In a
60 minute video, it’s tough to explore the problems of a large system. So we’re
going to play a little game here. I’m going to show you a small system one. The
code I’m going to show you is smelly. It’s a mess. And behind that mess are a
bunch of open-closed violations that make this code very difficult to manage.
The truth code I’m going to show you is so small that it’d be pretty
easy to fix. But I want you to pretend that it’s actually part of a much larger,
interconnected corporate accounting We’re going to focus in on just one function
in this large interconnected accounting system. It’s the function that prints
expense reports. Here it is. That’s quite a mess packed into that 26 lines, isn’t
it? I think to understand that mess, we should probably be looking at the unit
tests. And yes, there are unit tests. in episode 6 we discussed
how unit tests provide unambiguous documentation the first test shows us that
when you print an empty report whatever that is then what you get is a set of
totals at the bottom and a dated header at the top and I suppose that makes
some sense the second test gives empty meant in that first test. This test adds
an expense to the expense report. So presumably an empty expense report is
one in which no expenses have been added. In this test we’ve added the dinner
expense. We can seehe dinner showing up on the report and we can see it
reflected in the totals. So all this makes perfect sense. The third test adds two
4

meals to the report, We can see these meals on the report itself, and we can also
see their amounts reflected in the totals. The fourth test adds two meals and a
car rental, and we see all three of those expenses printed on the report, as we
might expect. But now the totals have diverged. The meal total counts only the
breakfast and the dinner, whereas the final total counts all the expenses. us
something interesting. It would appear that breakfasts over $10 and dinners
over $50 are marked with an X. The name of the test implies something about
overages, so perhaps the accountants desire some visual cue for expenses that
are over some particular limit. Now if you think those tests are well structured,
I’d like you to think again, because They’re based on a huge violation of the
single responsibility principle because they test the business rules through the
user interfaAnd that’s a huge no-no. Remember that episode I promised
you on advanced test-driven development? We’re going to talk more about
that there. Now let’s look at that code again. This is where the header gets
printed. Next, there’s a loop that prints all the expenses. And I’m just itching
to extract that out into a method named print expenses. Finally, there’s a bit of
code down at the bottom that prints out all the totals. And you know what
I’m thinking about them, don’t you? You see all those divide Actually, that
divide by 100 occurs two more times in this function. You think that might be
an opportunity to perhaps extract a method? And what do you think we should
call that method? How about, hmm, pennies to dollars? Now let’s dive right
inside that loop. First, we check to see if the expense is a meal. And if it is, we
add its value to the meal total. Then we use this horrible switch statement over
here to convert the expense type into a string of the corresponding name. We
use the string LT to represent an unknown type code. We never expect to
see the string TILT printed, do we? As a young software developer of 24 years,
I worked at a company where we tested the quality of telephone lines. up on
the console. Deep within the software that generated that report, we would
emit the word tilt whenever we ran across impossible situations. Of course, we
never expected the customers to see the word tilt. Nevertheless, we received
field service calls with relative frequency. What does tilt mean? Finally, we
print the expense. And you can see the format. It’s simple enough. There’s
a placeholder for the overage indicator, the expense type, and the expense
amount. The overage indicator is calculated with this horrible ternary operator
that compares the expense type and amount against these hard-coded overage
limits. The result is either an x or a space. And finally, we do the pennies to
dollars trick on the amount of the expense. We’ve already figured out what the
expense class is, but here it is n case you were wondering. It’s nothing
but a dumb data structure with an enum for the type and a constructor for
convenience. Clearly this code is a mess. That function is too large. It’s got
embedded constants within it. There’s duplication, and it’s loaded with single
responsibility violations because we mixed business rules with messages and
formatting. But there’s something very insidious hiding beneath that mess.
And that’s the problem with messes. They hide the rotten structures that lie
t is that rotten structure? This module violates the open-close
principle flagrantly. If I want to extend the business rules, I’ve got to reach into
5

this module and fiddle with it. If I want to change the messages and formatting,
I’ve got to modify the inside of this module. This module is closed for extension
and open for modification. For example, what if we wanted to add a new kind of
meal type, like a lunch or a snack? What’s the first line of code that would have
to change? Right, it’d be thn the expense class. We’d have to add the
new type there. modules in this large, interconnected accounting system depend
upon the expense class? It’s probably a lot of them. In fact, let’s stipulate that
it is a lot of them. Alright then, how many of those modules depend upon lunch?
Probably not very many at all care about lunch, and yet they’ll all be impacted
because we have to extend that enumeration. Every module that redeployed.
And if there’s a database representation for expense, the schemeto
have to change. And if the expense instances are transmitted to services, then
the service interfaces are going to have to change. Changing something that is
as core to the application as the expense class can be very burdensome to a
large system. In fact, the developers may consider it so indirect hack like maybe
adding a lunch flag to a meal attributes map. What design smell is this? It’s
rigidity. Even though the design change is small, the impact is huge, so the
system resists change. It’s rigid. lunch are just so important that we go
ahead and make them regardless of how difficult they are. The next problem
we’re going to face is even worse because that problem is going to be visible to
our customers and our users and our managers. Look at that switch statement
that selects the name or the conditional expression that looks at the meals or
that ternary operator that looks for overages. accounting system how many
other such switch statements and conditional expressions on the expense type
are scatred throughout the system consider that this system has to deal with
taxation reimbursement invoicing contracts and many other complications that
have to do with expenses so we can expect to find lots of switch statements
and conditional expressions that on the expense type. How will we find them
all? And when we do, how will we know how to modify them for lunches? How
likely is it that we’ll miss one? How likely is it that we’ll incorrectly modify
one? What design smell is this? It’s fragility. FragiImagine how awful it
would the taxation calculations. Of all the design smells out there, fragility is
the one we want to avoid the most. Why? Because when systems are fragile,
managers and customers come to the conclusion that the developers have lost
control and don’t know what the hell they are doing. But the problem is even a
fundamental change in approach. Their original business model had been to sell
a fully featured, end-to-end, enterprise-ready, absolutely complete accounting
system to their custers. It could be configured within limits, but it otherwise
had all the features anybody needed. Now they’ve realized that their target
market includes a bunch of small options in the system. So they’ve decided to
break the system up into components. They simply plan to give away the base
component, the engine that has no features, and then they’ll charge for all the
little plug-ins. Plug-ins for the meal expenses, plug-ins for special lunchtime
expenses, plug-ins for car rental expenses, and so on anorth. what they
want us to do is to create a set of gems or DLLs or jar files that we can deploy
and sell independently. Unfortunately we’re going to have to tell them that
6

the current structure of the system makes this impossible. We cannot cut the
expense report printing function up into components because it’s conditional
statements that depend directly on all the things that management wants us
to deploy separately. Look at this fanout diagram. It shows the print report
function and all the littlts of functionality that management would like us
to deploy separately. Notice those arrows. They show how the print report
function depends on that functionality with contains relationships. all that
functionality. Even if we extracted out all those functions, the arrows would
still point in the same direction. The print report function would still depend
on those extracted functions, and so we still couldn’t independently deploy
them. This is the design smell of immobility. There’s functionality out t
that we would like to deploy separately and conditionally, but we can’t do that
because of the way this system is put together. As it currently stands, deploying
this system is an all or nothing proposition. Rigidity, fragility, immobility, not
to mention just a plain old mess. This code is pretty bad indeed. So what
are we going to do to fix it? Are you ready for the lie? Of course there is a
way that we could have solved all these problems. If only the programmers
had known about good object-oriented dign principles. If only they had
known about the open-closed principle. Here, let me show you how it could
have been. experience the clean, cool, soothing flow of clean code as it was
meant to be. We begin with the expense class. Oh, the simplicity, the elegance,
the serenity and confidence. This class simply holds the value of the expense
and provides simple abstractions for the business rules such as is meal and is
overage. Dinner expense is nothing more than a finely tuned derivative. It
implements the is-meal and is-overage abstractions appropriately, without fuss,
without muss, just simple function implementations. And so too are car rental
expense and breakfast expense implemented. They’re almost too simple to talk
about. And then there’s the expense report class. No strings, no formatting,
nothing but the totaling functions that capture all the business rules. This class
is the epitome of single responsibility principle decoupling. Likewise, there is
the expense reporter class, which is responsible all the messages magical
constants. Nothing but simple lexical manipulations. It is the ultimate in single
responsibilities. I’d like to draw your attention to something down here in the
expense reporter. Notice how it gets the name of the expense from the namer.
That namer holds a reference to the expense namer abstraction. What a marvel
of minimalism! What a paragon of abstraction! carefully crafted little method
that separates the expense reporter and everybody else who wants to know the
names from thnames themselves and where are those names they’re here in
the expense report namer class oh the rye panache the flare the sheer ill-lond
of hiding this gritty type check in such Isn’t it a delight to the eye and to the
mind, a fusion of rigorous engineering and superlative artistry? And behold
how this marvel of software science, this masterpiece of abstraction behaves
when we posit the addition of a new meal expense, the lunch expense. Does the
expense class or any of its derivatives require modificat They require neither
recompilation nor even redeployment. They are oblivious to the change. So too
are the expense report and the expense reporter class, oblivious to this change.
7

No hand must move mouse, no fingers to press keys, no mind must ponder the
complications of the change, because no change is required. the lunch expense
requires only that we create the lunch expense class itself. There’s also a small
modification to the expense report namer class where we have to add an if-else
statement. Phaps you think this is a problem, a chink in our lovely edifice, a
ding in our beautiful structure, but no, look at the architecture diagram. The
expense derivatives and the expense report namer point inwards towards the
application. Those parts of the system that are open for extension and closed
for modification live on one side of the boundary and they are protected by
abstractions. Those parts of the system that must change implement those
abstractions from the other side of the boundary. This design is nowhere near
as smelly and fragile as the design in the previous segment. We don’t have
to go hunting for any switch case statements or if-else statements. We don’t
have to wade through lots of conditional logic looking to see whether or not we
can put our new feature in. All we have to do is add the new derivative and
add the name to the expense report namer class. You just get the idea that
you actually do know what you’re doing. But it’s better than that! Oh yes it
is! It’s much, much better tDo you remember that new business
model that our managers wanted to try? They wanted to give away the base
component and then treat all the features as plug-ins that customers could buy.
All the things they want to give away are on the far side of the line. All the
things they want to charge for are on the other side of the line. The plug-in
structure that we need has come for free. How perfect is this? How incredibly
suave, how brilliant and bold, how inseparable from the moral center of system
architecture. responsibility principle and creating the abstractions that enable
the open closed principle we’ve solved all the problems and we’ve created a
simple elegant beautiful practical and moral design Wow I’m going to go to bed.
now you just wait one cotton-picking minute I know you’re really smart and
all so I just got one little question for you I know that hyper whammy doodle
design here is certainly gonna help man a lunch expense off grant you that but
what if them our customers over there decide wevery meal expense over
$20 on weekends. What you gonna do about that, Smarty? Are you gonna
tell me you can add that feature without modifying any existing code there,
buck-hole? Yeah, that’s what I thought. Looky here, you don’t even have a
date expense class. How the hell are you going to know if it transpired on a
weekend? Uhhhh. . . And another thing you ain’t got is an abstract method
telling you whether or not that expense is transportation related. Uhhhh. . . . . .
And you’re also going to hhange that expense reporter class just to add
you. So that whole spiel you just unloaded on us about that var open closed
principle was just a load of dingoes kidneys wasn’t it? Okay okay now wait a
minute wait a minute nobody told me about any new feature that checks for
transportation related expenses If I had known, then I could have conformed to
the open-close principle. I could have arranged it such that the new feature
could be extended without modification. If only I had known. But you didn’t
knoid you? And how were you supposed to know something like that? Are
you trying to tell me that this here open-close thingamawhat’sit only works if
8

you already If you gotta be able to predict the future, it ain’t gonna be much
good to you, son. Now lookie here, Sonny. I don’t know who taught you to
program. But seems to me your education might be just a little bit short of
a full one, if you know what I mean. If I’ve learned one thing over the years,
Sonny, it’s that customers do the unexpected. t but those customers
will find the one thing you didn’t think of and that’s the thing they’re gonna
change on you he’s right of course it’s easy to sign abstractions that protect
you from future changes if you know what those future changes are going to
be but I don’t have that kind of a crystal ball any ability to change the one
thing you forgot to protect yourself from. This is the dirty little secret about
object-oriented design and the open-close principle that people don’t like to
talk aprotects you from change if you can predict the future.
What do we do about this? How can a principle be useful if it depends upon
presence, the ability to see the future? What good is the discipline of OO if it
requires perfect foreknowledge? Over the last 30 years, the software industry has
struggled to address this issue. As part of that struggle, we identified two major
approaches for the crystal ball. The first is to think really hard. You carefully
consider the customer and the problem domain. You create a domain model
that anticipates the customer’s needs and desires. You adorn that domain model
with abstractions making them open for extension but closed for modification.
And then you continue in that vein until you have thought up everything
that could possibly change. We call this approach Big Design Up Front, or
BDUF. And the problem with BDUF is that it creates large, top-heavy, complex
designs aren’t necessary. As useful and powerful as abstractions are, they’re also
expensive. They create itions. They disconnect those things that we think
of as being connected. They invert dependencies. And they make it hard to
follow from cause to effect. useful to us also make them costly. When we need
those abstractions, then the cost is bearable. But when those abstractions are
anticipatory and not currently needed, well then the cost can be overwhelming.
The cost of maintaining the large, over-engineered designs created by big design
up front is often prohibitive. I’ve seen many development teams hobbl to
near immobility designs that attempted to anticipate their customers’ future
actions. And remember, customers seem to have an uncanny ability to change
the one thing you forgot to protect yourself from. And when they do, changing
an over-engineered design will be a lot harder than changing a simple design.
design is both pragmatic and reactive. The best way to demonstrate that is
with a metaphor. Imagine you’re part of a squad of soldiers pinned down by
enemy fire. You’re hunkered down in a foxhol your buddies while bullets
whiz by overhead. If you could focus your fire on the enemy you could probably
break out and win the battle. The problem is you don’t know where You don’t
know what direction he’s firing from. And if you stand up to look around to
find him, he’ll cut you down before you’ve got a chance to focus your aim. And
so the sergeant makes an executive decision. He says, Johnson, stand up. And
now you know the direction that the bullets are coming from. Agile design is
like that.e simplest thing you possibly can. and then the customer
starts shooting at it with change requests. And then you know what kind of
9

change requests are likely. One of the best predictors of change is past change.
Once you know that something is likely to change, you can protect yourself from
that kind of change in the future. So instead of trying to out-think the customer
by predicting absolutely every change that customer might make abstractions
that would protect you from all those changes. What you can do instead is
simply wait for the customer to make a change and then invent the abstraction
that will protect you from any further occurrence of that change in the future.
Agile designers deliver something simple every week or so. And when customers
make changes, those Agile designers refactor the code, of change easy to make
in the future. Thus the system becomes open for extension, but closed for
future modification. Of course in practice we live somewhere between these
two extremes. We avoid big design up front, but we also avoid no design up
front. and creating a decoupled domain model up front. But we err on the side
of the small and the simple. Our goal is to establish the basic shape of the
system and not to think through every single little detail. If you overthink the
problem, you’ll create a lot of unnecessary abstractions that are very expensive
to maintain. often and refactoring based on changes that customers make. In
fact, this is where the open-close principle really shines. But doing this thout
a simple domain model will often leave you with a undirected, chaotic structure.
Let’s say that you’re part of a team of 10 developers. And you’ve been given a
new project, a Greenfield project, months. What design process best conforms to
the open-close principle? The team should spend a week, possibly two, scoping
out the initial requirements and coming up with a simple architecture and
domain model. The requirements should not be precise and the domain model
should not be detailed. The team mrite some code at this time, but the
focus is on the initial requirements and the architecture, not on implementing
features. Some teams call this iteration zero. In a future episode we’ll discuss
the structure and form of these initial requirements. For now we’ll simply call
them user stories. These user stories, and the architecture that surrounds them,
will not be correct in iteration zero. In fact, they don’t need to be correct right
now, because all we really need in iteration 0 is to establish aorward. Then
the team should begin to work in one- or two-week iterations. The goal of each
iteration is to get something executable in front of the users or their appropriate
proxies. When users see something execute, they start thinking of changes,
and those changes will be the basis of the abstractions that the team uses in
order to conform to the open-close principle. We’ll discuss the process for these
iterations in an upcoming episode. For now, just think of them as design and
programming time. Eachteration should begin with a simple design session,
where the team members look at the changes that have been requested, and
then figure out how to apply the open-close principle Then the developer should
refactor the code and add new features with those architectural changes in mind.
They should follow the discipline of test-driven development that we learned
back in Episode 6 and keep their code clean and easy to change. Each iteration
should see a growing conformance to the open-closed principle. Each iteration
should clarify and intensify the boundaries that describe the architecture and
the managed dependencies that cross those boundaries. Every iteration should
10

see more code that is open to the expected kinds of extensions and yet closed for
modification. If you follow these guidelines, you’ll be able to create systems that
are very flexible, robust, and mobile. However, this is engineering and not magic.
There’s no way to perfectly conform to the open-close principle. You just can’t
think of hing. No matter how closely you follow the rules, no matter how
careful you are, eventually the customers are going to think of some change that
will force major modifications throughout the structure of the entire system.
That’s just not feasible. Your goal is to minimize that pain. And that’s what an
open-close compliant design will do for you. Remember, the open-close principle
is the moral center of system architecture. And while moral perfection may not
ever be attainable, it’s certainly worth st for. Alright, so let’s recap. In
this episode we started by talking about Bertrand Meyer and his brilliant insight
that a module can be both open for extension and closed for modification. This
implies that you can create systems in which new features are added by adding
new code as opposed to changing old code. principle is at the moral center of
system architecture. I’d like you to consider that statement very carefully. To
the extent that a system is not open for extension and closed for modificatiohat system is immoral. We looked at one system that flagrantly violated the
open-close principle, and we saw how that violation led to all those awful design
smells like rigidity, fragility and immobility. And then we looked at a solution
that perfectly conformed to the open closed principle. Or so we thought. It
was simple. It was elegant. It was beautiful. And it was a lie! Then we saw
that in order to perfectly conform to the open closed principle, for in order to
create a system that is fully open to extension and closed to all modification one
must be able to perfectly predict the future but then we found that all hope
was not in fact lost that by using an iterative process with lots of feedback
and refactoring we could in fact develop systems that of a bar. And so we’ve
come to the end of yet another episode and boy we sure covered a lot of ground
didn’t we? I mean my head is spinning and I’ve got to go for a walk to clear
my head but we’ve still got so much to talk about there’s three solid pleft and then there’s all the component level principles and a raft of design
patterns there’s advanced test-driven development there’s the whole suite of
agile practices you’re not gonna want to miss exciting episode of Clean Code,
episode 11, the Liskov Substitution Principle. Come on you dogs! Time to go
out. Does the expense class or any of its derivatives require modification? Not
at all! Not at all, I say! Ha! Good. Action! I’m going to go get some food. I’m
going to go to the bathroom.

1ncle Bob, and this is Clean Code. In this episode. . . By Uncle Bob.
Uncle Bob. Enjoy. Uncle Bob. Welcome, welcome to Clean Code, Episode 11.
The Liskov Substitution Principle. Come on in. This is our fourth episode in
the series of the solid principles. Can I take your hat? Remember last time we
talked about Bertrand Meyer’s open-close principle? That was Bertrand Meyer’s
remarkable insight that a module could be both open for extension and closed
for modification. We figured out that it would be possito add new features
to a system by adding new code and not changing any old code. I told you that
the open-close principle was the moral center of system architecture, that good
architects and designers will strive to make their systems open for extension but
closed for modification. And then we looked at a system that just broke all the
rules and that exhibited all those horrible design smells of rigidity, fragility, and
immobility. that was perfectly conformant, or so we thought. It was simple, it
was beautiful, it was elegant, and it was a lie. Then we found that in order to
perfectly conform to the open-close principle, you have to have perfect foresight.
If you’re going to make a system that is infinitely extensible, you’ve got to
be able to perfectly predict the future. But we didn’t give up hope. realized
that if we used a process that was iterative, if we relied on lots of feedback, if
we delivered often, and if we used lots and lots of refactoring, then we could
well enough conform to the open-principle. Now, in this episode, after we
talk a little bit about wave-particle duality, we’re going subtyping, the Liskov
substitution principle. So first, we’re going to take a stroll through the history
and theory of types, from their mathematical underpinnings to their application
in computers. Now, I see all you ruby, groovy Python enclosure programmers
thinking that, no, this doesn’t apply to me. But it does. It applies to you.
whether the compiler checks those types or not. Next we’ll talk abypes.
We’ll discuss Barbara Liskoff’s critical insight into the definition of subtypes.
We’ll talk about why that definition is important and the implications of that
definition for static and dynamic languages. the definitive case for the Liskov
Substitution Principle, and we’ll see what can go wrong when you use inheritance
and subtyping intuitively instead of according to Liskov’s definition. This will
lead us to some heuristics, examples, and rules that will help us detect and solve
violationsskov Substitution Principle. Finally, we’ll look at a larger case
study to create substitution violations that you don’t recognize right away. And
then we’ll see the terrible damage that’s done by such violations. And in the
end, we’ll look at some simple ways to either avoid or repair that damage. So
you put your thinking caps on and sharpen your pencils, because we’re about to
submerse ourselves in the fascinating world of the Liskov Substitution Principle.
As we learned last time, in 1900 Maxovered that although light
moves in Maxwell’s waves, it’s also absorbed and emitted in discrete amounts
of energy. Einstein went on to show that this discreteness in the light waves
was an attribute of the but not of the atoms that were emitting and absorbing
them. That is, the light waves were organized into discrete quantities of energy,
which Einstein called light quanta, and we now call photons. So somehow, light
is both a wave and a particle. But we should be clear about what the word
particle meanard little nugget. Instead it means discrete and indivisible.
1

A photon of light is a bundle of energy that cannot be split apart. It always
equals Planck’s constant times its frequency. What does it mean for a particle
to have a Light travels in waves. It carries its energy in waves. But when it’s
forced to deposit that energy on some surface or some entity, it always does so in
discrete amounts at discrete point-like locations. And that discrete amount and
that discrete location is the photon. Thatâr, isn’t it? Maybe an example
would help. This is my green laser pen. I use it when I’m giving talks. It’s
very bright. This laser pen is a photon gun. It fires a stream of photons in a
very narrow beam. The number of photons it fires is huge, but discrete. and
they travel in a wave towards the wall. When that wave strikes the wall, the
wave deposits its energies upon the atoms of the wall in discrete amounts upon
discrete atoms. Those atoms then reflect those photons back outwards towards
our eyes,e see the green spot on the wall. on this laser pen that would
adjust the rate at which the photons were fired. Maybe I could turn that knob
all the way down so that it fired one photon a second, kinda like that. And then
the blinks you would see on the wall would be one photon each, depositing its
energy at a particular discrete location with a very particular discrete energy.
Now let’s crank the firing rate of this laser back up to trillions of photons per
second and we’ll shine it through something ts got a bunch of tiny little slits
in it, like my comb. What should we see on the wall? Presumably the beam
will pass through the slits and strike the wall and so we should see one green
spot on the wall. see the shadow of the slits. We can illustrate this by using
this flashlight and a paper plate with two big holes in it. We can still see the
flashlight beam, but only the part that’s getting through the two holes. But
now let’s go back to my laser, and instead of a comb, we’ll use this diffraction
g, in it. 13,500 per inch. We’ll shine that laser through this again and we
get stripes, spots. Look at that. And of course, that’s exactly what you’d expect
if the light were traveling in waves. You see, the waves pass through the slits in
the diffraction grating. They break up into a bunch for each slit. Those little
waves move towards the wall, but as they do so, they interfere with each other,
resulting in this characteristic pattern of wave interference. That, my friends, is
an interference patter if I take the slits away, I get one nice little spot on
the How cool is this? So now let’s crank our laser pen down so that it’s only
firing one photon per second. What do we see? Well, we see one flash per second
all right, but the location of those flashes is strange. They seem to be all over
the screen. But if we accumulate all those little flashes over an hour or so, we
find something really startling. We see the interference pattern. Each photon
travels as a wave. That wave passes through the slitd breaks into many
waves, which then interfere with themselves. with a discrete energy. Where will
the photon land? There’s no way to know. It’s completely random. But the
odds are that the photon’s going to land where the interference pattern is bright.
The odds are very low that the photon will land where the interference pattern
is dim. Did you hear what I just said? I said odds. Odds. that determines
where a photon will land? Odds! Odds in the shape of an interference pattern.
Apparently the wave hoton is a wave of odds, a wave of chance. A light
wave is not a wave through the ether, it’s a wave of probabilities. my head hurt.
2

And so these waves of probability propagate through space and interfere with
each other, leaving an interference pattern of probability on the screen. The
position of the photon is undetermined until that photon strikes the wall and
deposits its energy. The position of the photon is uncertain. And the principle
behind that uncertainty will be our topic for next time. Alrit, now I want you
to be a little bit patient, because what you’re about to hear is going to sound
like another science lecture. But it’s not. to the Liskov substitution principle.
In the second half of the 19th century, a German mathematician by the name of
Friedrich Ludwig Gottlob Frieg decided to treat mathematics the way Euclid had
treated geometry. His goal was to derive all of mathematics from a few simple
postulates. a paper whose title in English was a formal language for pure thought
modeled on hmetic it was a masterpiece Frigga had created a formalism
that allowed him to describe all of mathematics integers fractions functions Not
only could Friege describe mathematics with his formalism, he could describe
virtually anything. This formalism of his resolved a whole series of problems that
had plagued logicians and mathematicians for years. Twenty-three years later
Bertrand Russell discovered the first chink in Friege’s formalism. He showed
that it was possible to create paradoxical statements usg statements that could
be proved neither false nor true. Russell’s paradox looked like this. It can be
described with this simple question. Does the set of all sets that don’t contain
themselves contain itself? So, now you should hit pause and then play that over
again. And then hit pause again play it over again and keep doing that until you
understand it. Or perhaps you should look at it this way. If your mother only
cooks for those who don’t cook for themselves, who cooks for your mother? Or,
if yt it to be really simple, this statement is false. Clearly, the question
cannot be answered. In fact, the question is caught in a logical loop. There’s no
resolution to that loop. If you were to write a program to solve it, that program
would loop forever, recursing infinitely, and would blow the stack. intuitively
intuited that the solution to the problem was to restrict the types of things that
could be operated upon by functions. It soon became clear that the loops could
be prevented by expressing typein a hierarchy that had no cycles. This work
was carried forward into the 20th century by a whole host of mathematicians,
including Russell. quote from the work of Kurt Gödel in 1944. Yes, yes, yes,
yes, yes. By the theory of simple types, I mean the doctrine which says that
the objects of thought are divided into types, namely individuals, properties of
individuals, relations between hierarchy for extensions, and that sentences of the
form, A has the property phi, or B bears relation R to C, etc., are meaingless if
A, B, C, R, and phi are not of types fitting together. Now, if you squint enough,
that sounds like the definition of objects and function signatures in Java. a hint
of inheritance and polymorphism in there. Now guess who was working in the
field of mathematical logic at the time? It was Alan Turing of course. The
year was 1936. He had just finished his paper introducing the Turing machine.
Have you read this book? The Annotated Turing by Charles Petzold. It’s a
fascinating book, and if you havet read it yet, you should. It will convince you
that Alan Turing had worked out many of the principles of programming, even
though that was never his intent. As the century of progress progressed, the
3

overlap between the theory of types and the practice of computing continued to
grow. Fortran was designed in 1953, paper and only one year after I was born.
Fortran had a pretty rudimentary type system but what types there were were
strongly enforced. For example you weren’t allowed to mix integers and re
numbers in the same expression. COBOL allowed very fancy data types to be
created but didn’t from very humble beginnings to become the progenitor of
the type systems in Pascal, Modula, and even C++. In short, the type systems
of modern languages can trace their origins back to the type theory of Frieg,
Russell, and Gödel. And the operation of modern digital computers use a logical
structure that Frieg would recognize. Fascinating! Consider an integer. What’s
inside it? Is it 16 bits? 32 bits? 64 bits?does it use 1’s complement
math or 2’s complement math? Where’s the sign bit? And might it perhaps
be binary coded decimal? to the integer that represents 2 results in the integer
that represents 3, you don’t care. It doesn’t matter what’s inside a type. All
that really matters are the operations that can be performed on that type. So a
type is really just a bag of operations. Do you care what the internal structure
of a floating point number is? Or do you just care that 2.0 is 0.5. Again, we
doare what’s inside a type. We only care what a type can do. We
care about the functions and operations that it provides to us. So, what is a
type? From the outside looking in, a type is nothing but a bag of operations.
Oh, there may be data within it, existence of that data is hidden behind those
operations. And that, of course, is exactly what a class is. From the outside
looking in, a class is nothing but a bunch of methods. And the data within is
private and hidden behind those methods. Does this statemt in C define a
type? Clearly not, because it doesn’t define a set of operations. All it defines
is a data structure. For example, we could define distance, translation, and
rotation operations as follows. Now we’ve got a type, especially if we hide the
definition of the data structure and prevent anyone from manipulating it unless
they use the operations that we defined. Of course, in order to do that, we’ll
have to supply some getters and setters. This was really a pretty common style
of C programmiing the 70s and 80s. I was a programmer during that
time, writing lots of C, and I remember that we also used another clever trick.
type is identical to the point type in its first two elements. And this means that
we can cast a described point to a point and then pass it into any operations
of point without any danger. So what’s the relationship between point and
described point? Clearly, any function that takes a point into. But the reverse
isn’t true. Here’s a function that takes a described point u can’t pass
a point into that. This means that the relationship between the two types is
asymmetrical. Described points can be used as points but points cannot be used
as described points. And this asymmetry of usability defines the relationship.
That is the subtype relationship. Described point is a subtype of point. This
notion of subtypes had been trying to emerge from languages since the times of
Fortran. In some sense, for example, an integer is a subtype of a real number.
And Fortran made some concsions to this. loading point numbers. There were
other attempts to deal with subtypes in languages such as ALGOL. The writings
of the day referred to things like discriminated unions and other structures that
4

approximated subtypes. But it was in Simula 67 that the notion of a subtype
really came to the fore, because and inheritance appeared in a way that we’d
recognize today. Indeed, the C++ inheritance scheme and all those that derived
from it can be traced directly back to that language. It wasn’t l 1988 that
a formal definition of subtype was created. of the ACM and was authored by
Barbara Liskoff. I didn’t learn about this definition for another four years. It
was in 1992 and I happened to be sitting in the San Jose airport reading Jim
Copleen’s wonderful book Advanced C++ Programming Styles and Idioms and
in that book I read these words. If, for each object O1 of type S, there is an
object O2 of type T, such that for all programs P defined in terms of T, the
behavior of P is unchanged when O1 ubstituted for O2, then S is a subtype
of T. but eventually it sunk in. What Liskov was describing was that asymmetry
of usability that we talked about in the previous segment. Subtypes can be used
as their parent types. Or to say this a different way, imagine that you’ve got a
bunch of users, we’ll call them you, and they can use a type that we will call
And then let’s say that we’ve got a subtype of T, which we will call S. That
means that all the users, U, should be able to use S. Without knowingt
may seem like an obvious restatement of basic polymorphism. But as obvious
as it may be, as we’ll see in the next segment, consistently get wrong. By the
way, as I sat in that San Jose airport reading Coplin’s book, I noticed that he
called Liskov’s idea the Liskov Substitution Principle. And that got me thinking.
principle. It had a certain ring to it. It sounded like the Pauli exclusion principle
or the Heisenberg uncertainty principle, which, by the way, we’re going to be
studying in the next eAnd that gave me an idea. It made me think,
well, maybe there are other software principles out there like this one. When
I read of the idea that eventually grew into the solid principles. Notice that I
used the inheritance arrow in the UML diagram to describe this principle. But
is inheritance a necessary element? Well, in languages like C++, Java, and C
Sharp it certainly is because those statically typed languages on inheritance to
provide polymorphism. The only way that you can polymorphically deploy a
method call in those languages is if the caller invokes the method on an instance
of what it believes to be a base class but is really an instance of a class derived
through inheritance. But in dynamically typed languages, the rule is different.
Instead of invoking methods, we say that we send messages. The effect is the
same, but the connotation is helpful. In a dynamic language, if you want to
call a method, I mean send a message to an object, the compiler doesn’t know
the type of that object. So the lauage has to wait until runtime to determine
whether or not you can call that method. or not you can send that message. If
the object can respond to that message, then the method is invoked. Otherwise,
a runtime error occurs. So no, no inheritance is necessary, so long as the two
objects respond to the same message they can be used polymorphically. This
is often called duck typing. and quacks like a duck and swims like a duck. I
call that bird a duck. Rubber ducky, you’re the one. You make bath time so
mucfun. I don’t remember the rest of it. Rubber ducky, I’m simply in love
with you. Now remember what a type is. A type is a bag of methods. a type, it
too is a bag of methods. And since that subtype must be substitutable for its
5

parent, it must have the same methods in it that the parent has, even if they
have different implementations. In statically typed languages, we achieve this by
using inheritance. In dynamically typed languages, we achieve it by writing the
same methods into the subtype. But in he subtype is that it’s substitutable
for its parent. So, from this point on in the episode, we’re going to use that
inheritance arrow to mean subtype. When the Liskov substitution principle is
violated, the result is usually a refused That term is one of the code smells that
appears in Martin Fowler’s wonderful book, Refactoring. If you haven’t read
this book, you should, and don’t let the 1999 date scare you off. This book is
as relevant today as it was back then. I remember reading it when atteey practices that my son was doing, and although the parents sitting next
to me might have thought that I was going on out on the ice? Often as not, my
cheers were related to what I was reading in this book. A refused bequest occurs
in dynamically typed languages when you send a message to an object and the
object doesn’t have the corresponding method. Most languages will cause some
kind of exception to get thrown. So for example, in Ruby, let’s say that I that
I create an instance of this class and I to send it the f message. It will of
course throw a no method error. That’s a refused bequest. A more subtle form
of refused bequest occurs when a method in a subtype does something that the
client of the supertype does not expect. that users of the base class don’t expect.
Or, the derived class might cause a side effect that the users of the base class
don’t expect. Clearly, that kind of refused bequest can occur in both static and
dynamic languages. Let’s look at a classic case. Let’s say that weass
named Rectangle that’s used by some program. This class has instance variables
such as height, width, and top left point. It also has methods such as area and
perimeter. And of course it has the normal array of getters using this rectangle
class for years. There are instances of rectangles getting passed around all over
the place. Now let’s say that we discover a new requirement for squares and we
decide that in order to meet that requirement we need a new class named square.
Square, between the recle and the square. Clearly, a square is a rectangle.
And we all know what those magic words, is a, mean, don’t we? It means that
in a statically typed language, we’d use inheritance. And in a dynamically typed
language, we’d use duct typing. And in either case, square would be a subtype of
rectangle. inheritance we can already see a problem rectangles got two variables
height and width square is going to inherit both of them which means square
is going to be too large now look memories cheap maybe it t bother you
that instances of square have one extra variable but it ought to because it means
there’s But never mind that. I mean, maybe we just don’t care about the extra
memory. It turns out that Square is inheriting something even stranger than
that extra memory field. Square is inheriting setHeight and setWidth. What
does Square want with a setHeight and setWidth method? What it really wants
is a setSide method. to it, but it would still be inheriting set width and set height
from rectangle. And th just strange. Now you Ruby programmers may think
you just dodged a bullet, because you don’t have to use inheritance to inherit the
rectangle into the square. And you’re right! is a duck type. It’s going to have
to walk, swim, and quack like a rectangle. It will be passed around the system
6

through dozens of instances as though it were a rectangle. And that means it’s
going to have to have set width and set height operations. So we’re stuck with
these methods that don’t make a lot of sense foBut at least consistent
with the behavior of a square by overriding them to preserve squareness. In the
Java case, we can override the two methods to set both the height and the width.
In the Ruby case, we can override both methods to set the side. And so now,
though some of the methods seem out of place, square, and the rectangle behaves
like a rectangle. So, all is well. Well, maybe everything isn’t all well. Imagine
that there’s a module in our system that calls set width on what it believes is
a recle. Does that module have the right to expect Of course it does. It’s
using a rectangle. And when you set the width of a rectangle, the height doesn’t
change. But if a square gets passed into this module, then when the module
changes the height, the width will change. And that’s something this program
didn’t expect. What happens when you call a function and it does something
you don’t expect? We’ve got a name for this. We call it undefined behavior.
Do you know what the definition of undefined bUndefined behavior
means that it’s going to work perfectly in your laptop and in your development
environment but as soon as you ship it to the customer Or if you’d rather, it
means you’re going to spend weeks debugging some problem that occurs once
per day or so. Or if you’d rather, it means that you’ll have to dig through
megabytes of stack traces trying to figure out why the heap got corrupted a
billion instructions ago. someone passed you a square when you were expecting
a rectangle. What willow will you fix it? You know how you’re going
to solve this, don’t you? You’re going to put an if statement in. An if statement
with an instance of. You’re going to ask that rectangle square. And that hangs
a dependency from the midst of our program onto the new class square and that
is an open-close principle violation. Every refused request, every violation of
the Liskov substitution principle is a latent violation of the open-close principle
because in order to repair the damage the refused bequee going to have
to add if statements and hang dependencies upon subtypes. And when the
open-close principle is violated, well, you remember what happens then, don’t
you? The software gets rigid and fragile. And then managers and customers
will come to the conclusion and don’t know what the hell they are doing! So
what’s the solution? How can we represent both squares and rectangles in our
software? Some folks have suggested that in static languages we should invert
the inheritance relationship and havangle derived from square. this solves
one of the problems, sort of. It means that we won’t have too many variables
in the rectangle. The name of the variable in square is going to be side, but a
rectangle needs two variables, so what should we call the other one? Other side?
But the real problem square has the right to expect that when he sets the side to
5, the area will be 25. If you passed him a rectangle, that wouldn’t be true, and
so there’d still be a refused bequest. There’d still be a violathe Liskov
substitution principle. Another common solution to this problem is to make the
squares and the rectangles immutable. The problem goes away. Well, much of
the problem goes away, not all of it. I mean, the square still has one variable
too many, and the names height and width are still going to be prominent in
7

the square. So making the types immutable doesn’t solve everything. The best
way to avoid all these difficulties is to treat square and rectangle as completely
different types, never tryo pass a square into a function that expects a rectangle.
I’m sure you think that’s nuts. I mean, isn’t a square a subtype of a rectangle?
Isn’t a square a rectangle? Doesn’t the is-a relationship hold? Of course it does.
A square is a rectangle. A square is a bona fide, absolute, perfectly about it.
The problem is that this is not a rectangle. It’s a piece of code and that piece
of code represents a rectangle but it is not a rectangle. Here’s the thing about
representatives. For example, imag who are getting divorced. Each
one of them has a lawyer which represents them. It’s very unlikely that those two
lawyers are themselves getting divorced, because the representatives of things do
not share the relationships of the things they represent. So while geometrically a
square is a rectangle, The software representatives of those concepts don’t share
the subtype relationship. This may bother you at some deep level. Perhaps you
think the whole point behind OO is to create models of the real worldd
if you can’t model the ISA relationship, well then, what’s the point? But no
real world principle has been violated here. relationships of the objects they
represent is a real-world principle. It’s important to remember that when you
create models in software, the things in your models are mere representatives.
Here’s another example. Consider the type integer, and remember that the
internal representation of integer is not important. Well consider the class real
number. It is undeniably true thatnteger is a subtype of a real number.
You can pass integers into any function that accepts a real number. So every
integer is a real number. It’s also true that every real number is a complex
number. A function that can manipulate a complex number can also manipulate
a real number. But every complex number holds two real numbers inside it. One
for the imaginary part and one for the real part. This makes a really pretty
UML diagram. And the UML diagram makes perfect sense until you convert it
to code. Onceou convert it to code, it becomes nonsensical just like Russell’s
Paradox. This is a refused bequest of the first order. You can’t even create an
instance of these objects without blowing the stack. So there’s a perfectly good
example of a real-world model that makes perfect sense in the real world, but
makes no sense at all inside the computer. And why? Because that integer class
is not actually an integer. It represents one. The real number class is not a real
number. It represents one. The complex represents a complex number.
And the relationships between objects are not shared by the representatives of
those objects. These examples have all been pretty academic. example and we’ll
see just how damaging a violation of the Liskov substitution principle can be.
However, before we leave the realm of the academic examples, there’s one more
I should share with you, and it’s actually much more pragmatic than the others.
You’re not going to like it. In fact, you’ll struggle to try and prove it wron’ll fail. S is a subtype of T. A list of S is not a subtype of a list of T. To
make this concrete, let’s suppose that circle is a subtype of shape. Then if we
create a list of circle, we cannot pass that list into a function that expects a list
of shapes. because that function may put a square in the list. Here, look at this
code. Notice that the function g creates a list of circles, and then it passes that
8

list of circles into the function f. But the function f takes as its argument a list
of shapesd then in the body of f, it puts a square in the list. Fortunately,
the Java compiler makes this an error, because a list of circles cannot be passed
as a list of shapes. This is another example of the principle of representatives.
A list of shapes represents a group of shapes. The list of shapes is not a shape
in and of itself. And the representatives of things do not share the relationships
of the things themselves. On a side note, the composite pattern adds a lovely
little wrinkle to this issue. We’ll  looking at that in an upcoming episode.
This principle can be generalized further. Given that S is a subtype of T, then
the generic class P is not automatically a subtype of the generic class P. Hwyl.
We’ll be right back. We’ll be right back. We’ll see you next time. 23 years
later Bertrand Mussel Bertrand Mussel Bertrand Mussel I grabbed my eyebrow
Alright, alright, oh We call it undefined behavior Do you know what unbehame
define your means? Do you know what unbehame define your means? The knife
ja jams on you and you can’t pull it out. Is a real world principle. And
now I have no idea what else to say because I’ve forgotten my lines. Now it
should be clear that if you carefully express your pre and post conditions then
someone will flush the toilet right while you’re talking. And you get plumbing
type safety. There will be no 2 a.m. Frank Pone calls. I wonder who Frank Pone
is. Frank Pone, Frank Pone, calling Frank Pone. In the end, the only way to
avoid the exception is to put the dreaded if ce of statement in.

9

Hi, I’m Uncle Bob and this is Clean Code. So how do you know if you’re violating
the Liskov Substitution Principle? not setting yourself up for a refused bequest
and the horrible open-closed violation that follows from it. Here are a few simple
heuristics you can follow that you’ll find helpful. First, remember that if the
base class does something, the derived class must do it too and it must do it in
a way that does not violate the expectations of the callers. that you cannotexpected behaviors away from a subtype. A subtype can do more than its parent
type, but it can never do less. This means that whenever you have a derived class
that has degenerate functions in it, functions that don’t do anything, then you’ve
possibly got a Liskov substitution principle violation, especially if those functions
were Now look here children, not all degenerate implementations are a violation,
so you can’t make this a hard and fast rule, but you should all be suspicious
whenever you see aerate implementation. A more blatant clue occurs when
a derived function is written to unconditionally with the Liskov substitution
principle, because the author of the derived function clearly doesn’t want you to
call it. But how are you supposed to know that you’re not supposed to call that
function when all you know is that you’ve got the base class? How are you going
to stop that exception from being thrown? In the end, about all you can do is
use the dreaded if instance of statement. Another indi that the Liskov
substitution principle being violated is the presence of the dreaded if instance of
statement. This isn’t always a violation. There are sometimes good reasons to
check the type of an object, but it’s very suspicious. When is it safe to check the
type of an instance? There’s only one rule. Why would we bother to check the
type if we already know it? Only if the compiler has forgotten it. For example,
consider this function that adds a new time card to a list of time cards within an
houployee object. Hourly employee derives from employee Our function
takes the ID of an hourly employee and uses it to fetch that hourly employee
from the employee gateway. But the gateway returns the hourly employee as the
type employee. But we know that this ID must be for an hourly employee. If
not, then the function makes no sense. know to be true. This use of if instance
of is harmless. It added no new dependencies to the function. This function
already needed to know about hourly employee and so no new information has
been added. The if instance of simply reasserted information that the compiler
had lost. of becomes a problem when there’s a chance for an else if instance
of. Remember the square rectangle problem from the previous segment? We
added an if instance of statement in that problem because we were in a module
that was using a rectangle, but somebody passed us a square. We weren’t just
asserting that we had a rectangle. We were questioning whether or not the object
was a rectangle or a square. that begs the question, what else might that
rectangle be? Are we going to have other derivatives of rectangle in the future?
For example, are we going to have 2 to 1 rectangle? 3 to 1 rectangle? This kind
of structure is called a type case, and clearly it can become a significant problem.
It should be replaced with polymorphic dispatch. In a future episode, we’ll talk
about the visitor pattern, and how you can use it to safely remove type cases
without polluting your hierarchies with irrelevant methods.  you see a type
case, or anything that looks like it might become a type case, it’s very likely a
1

violation of the Liskov substitution principle that’s driving it. As we noted before,
statically typed languages achieve subtyping through the use of inheritance. And
subtyping is what gives us the open-close principle, for architectures defined by
boundaries. But inheritance is the strongest relationship that can exist between
two types. When you derive from a class, you inherit everything that’s insit class, including all of its dependencies. The design smell of rigidity is caused
by unrestrained accumulations of dependencies, Inheritance breeds rigidity. We’ll
see more about this when we study the dependency inversion principle in an
upcoming episode. For now, it ought to be clear to you that when you inherit
a base class, you drag along all the baggage that’s inside that base class. Now
what this means is that the relationship that gives us flexibility also makes
us rigid. All that open-close prile stuff that depends on subtypings, we
get that from a relationship that also gives us inflexible structures. This isn’t
the case for dynamic languages like Ruby or Python or Smalltalk because they
don’t rely on inheritance for subtyping and that means that they can create
flexible structures This is one of the reasons that dynamic languages like Groovy
and Ruby and Python have become so popular lately. Using those languages,
it’s possible to conform to the open-close principle and build highly flexiructures without experiencing increased rigidity. But dynamic languages have
a different problem. Java compiler would catch at compile time. This is why
languages like Java, C Sharp, and C++ are considered to be type safe. If you
make a type error in Java, the program won’t compile. If you make a type error
in Ruby, the program crashes. That’s a huge difference, and it’s proven to be a
significant disincentive Indeed, for years programmers chose the rigidity of type
safe languages over the flexibilitynamic languages because they simply
could not tolerate the risk that their programs would crash for reasons that
were so easily detected by a type safe compiler. is the topic we studied back in
episode 6, test-driven development. This discipline was invented and refined by
programmers of dynamic languages, and for obvious reasons. When you don’t
have a type checker, you do your own type checking. However, when test-driven
development was eventually adopted by the programmers of static languages like
Java,hemselves an obvious question. If unit tests protect you from type errors,
why do you need a language that imposes rigidity on you to do it? And that is
how the rebirth of dynamically typed languages began. But type-safe compilers
do not find all type errors. the type errors that can be found through static
analysis. For example, the Liskov substitution principle violation that we saw in
the square and rectangle problem, that can’t be found by a Java compiler or a C
sharp compiler or a C plus plus compileusing static analysis. The reason for this
is that types are Remember that a type is a bag of methods. And while it’s true
that the signatures of those methods are part of the definition of the type, the
behavior of those methods is also part of the definition of the type. It was in the
80s that Bertrand Meyer set about to address this issue. The book that he wrote,
Object-Oriented Software Construction, on resolving this issue. The technique
he used he called design by contract. The idea actually derivesrom the work of
C.A.R. Hoare and the type theories of Frigg, Russell, Gödel, et al. Every type
has certain invariants which can be stated as Boolean expressions that must
2

always be true. and width of a square must always be equal. Every function in
a class can be surrounded by preconditions and postconditions. Preconditions
are Boolean expressions that must be true before the function can be called.
Postconditions are Boolean expressions that must be true when the function
returns. If you carefully exprss your pre and post conditions, then you’ll be
providing precisely the functions necessary to do dynamic type checking. If you
encounter a problem at runtime, it will be discovered instantly by your pre or
your post conditions and pinpointed for you so you can quickly fix it. Meyer
actually wrote the language Eiffel around this concept. conditions and invariants,
and the language would call those functions for you at just the right times, and
combine them with just the right logical operations to ensure namic type
safety. Were it not for test-driven development, design by contract might have
taken hold. But as it happens, test-driven development is a far more general, if
perhaps Nowadays, it’s test-driven development and not designed by contract.
That is the primary means of preventing dynamic type errors. Consider a system
in which a very old suite of programs called the file movers using modems. The
FileMover programs use the interface named Modem to communicate with all
the different kinds of modems, cluding the Haze modems, the U.S. Robotics
modems, and even the old Zoom modems. The modem interface has methods
like Dial, Hang Up, Send, and Receive. The FileMover programs call dial to
connect to the systems between which the file will be moved. Then they call
send and receive to enact the file transfer protocol. And when they’re done
moving the file, they call hang up. The FileMover programs are very fragile.
Anytime anybody touches one for any reason, they break in a whole bunch of
places. to touch t FileMover programs. Official rigidity has set in. However, a
new requirement has come to the fore. Some of the nodes in our network have
decided they need to move away from dial-up modems and start using dedicated
modems instead. Dedicated modems are modems that you don’t need to dial.
They’re permanently connected. Another group of users in our company has
been using dedicated modems for years for a whole range of other applications.
This group is called the dead users. The dead users use the dedicatedem
interface, which has send and receive methods. The FileMover programs have
never used dedicated modems before, change. So now the FileMover programs
are going to have to use dedicated modems. Management has recently heard
about the open-close principle, and they like the idea. They like the idea that
they can extend the behavior of FileMover without modifying it. They see this
as a way to continue their policy of official rigidity. They like the idea that
we rate of. So we’ve been charged with gettinghe old FileMover programs
working with the new dead modem interface without touching any of the old
FileMover programs. Now the easiest way to get this to work is to simply derive
the dead modem interface from modem. we could implement the hang up and
dial methods to do nothing. The file movers will still call them, of course, but
those calls will be ignored. And we’ll just stick dummy phone numbers in the
database for the dedicated network nodes. Yeah, those dead users are certainly
gonna be angry becauswe’re changing the dead modem interface. And that’s
gonna force them to recompile and redeploy all their applications. Well, that’s
3

too bad and really sad for them, but it’s just one rebuild and redeploy and then
we’re done. And everything works. Management declares us to be geniuses.
We’re all promoted and given big raises. The dead users hate us. But otherwise,
life is good. But as the weeks go by, the users start to report more and more
strange behaviors. About once per day, one of the movs corrupted.
Its file length is one character too long. At first, we think this is some kind of
hardware problem. But as the weeks go by, we realize that the only files that
ever get corrupted modems. After a few months the situation has gotten to be
critical. Every customer who uses a dedicated modem has begun to complain
about this issue. Management is up in arms. They’re deeply concerned and
they’ve told us that we’d better get to the bottom of this as quickly as possible.
We suspect that the faultfriends the dead users and we ask them if they’re
sure that their modem driver actually works this doesn’t help our relations with
the dead users at all they calmly tell us that they’ve been using this driver for
years and they’ve never had any problems with it we point out that we added
no new executable code from the file movers into the dedicated modem driver.
So the problem’s gotta be in that driver. The dead users glower at us, but they
agree to take a look. The next day, they come back to usxplanation.
There’s nothing wrong with their modem driver, they tell us. The problem is
a race condition in the file mover programs. It turns out that the FileMover
programs were not written to expect the modems to receive characters until
after Dial had been called. But the dedicated modems can receive characters at
any time. So every once in a while, an unsolicited character sneaks in, and the
FileMover programs don’t realize that this character was received before they
called Dial. us that we’re go have to change the FileMover programs to
ignore characters until dial is called. They’re right of course, but that leaves us
with a real dilemma, because now we’re going to have to change those FileMover
programs, and we were told not to do that. What are we going to do? What are
we going to do? But then we get a really clever idea. into that dedicated modem
class. That flag would not allow characters to be received until you called dial,
and it would stop them again once you called hang up. So we headthe lab to
try this out. We force the race condition to happen. We show that before the
fix, the file movers do in fact add extra characters every once in a while. But
after the fix, no such additions occur. We’ve got the solution. It works. So now
all we have to do is tell the dead users that they have to call dial and hang up.
I don’t think they’re going to be very pleased about that. You want us to what?
You want us to call dial? What phone number do you want us to them that this
is a simple fix, i big deal, and besides, management has mandated that no
one is allowed to change the FileMover programs. We beg, we plead, we promise
to buy lunch for them for a year, but they don’t want to have lunch with us.
They don’t want to see us again. They don’t want to have anything to do with
us. their door again. And it all works perfectly. There’s no more file corruptions,
there’s no more problems of any kind. And after a while, everybody kind of
relaxes and things settle down and go back to normal. Aose annoying
2am prank phone calls aren’t happening quite so often anymore. And that makes
them realize that they can’t use 10 digit phone numbers anymore. Clearly this
4

means that the dial method of the modem interface is going to have to change.
It can’t take a 10 digit array anymore. It’s going to have to be changed to take
a variable length string. This means that the FileMover programs are going to
have to change. So instead they’re hiring some very expensive consultants. We
are told to makges to the modem interface, the modem derivatives,
and the dedicated modem class. I think they took the news quite well. is a
subtle violation of the Liskov substitution principle. There is no way to make
the dedicated modem subtype perfectly substitutable. The dedicated modem
can only be made to work with the file movers if it violates the expectations of
the dead users. It can only be made to work with the dead users if it violates
the expectation of the file movers. there’s no way to remove the refusedequest.
The first hint, of course, was the degenerate implementation of the dial and
hang up methods. Those degenerate methods overrode other methods that had
real behavior, and when we removed that real behavior, we set the stage for
the refused bequest. class into the battle between the dead users and the file
movers, they created a long distance dependency that resulted in a fragile and
rigid system. Some of you have already guessed that one of the solutions to this
problem is to use an adapter, which is a pattern by the way that we’re going to
be studying in a future Rather than derive the dedicated modem from modem,
we could derive an adapter from modem and then delegate just the send and
receive methods to the dedicated modem. That adapter will contain the Boolean
flag that protects the FileMover programs from the race condition. Notice that
the adapter has no effect at all on the dedicated modem class. we’re never going
to have to talk to those dead users, and our phone’s not going to be ringing
.m. All the refused bequests have been eliminated. All the subtypes are
perfectly substitutable. There is no Liskov substitution principle violation. Now,
you might complain that this is an ugly hack. And you’re right. It is an ugly
hack. But look at the direction of the dependencies. Notice that they all point
away from the ugly hack. Nobody in the system knows that that ugly hack exists.
Except of course for main. Remember way back in episode 4 we talked about
how main should live in a separate module tt’s behind a boundary and that
all source code dependencies that cross that boundary should point away from
main? The dead modem adapter is only known to main. The rest of the system
has no idea that it exists. If you need an ugly hack, make sure you isolate it from
the rest of the system by pointing all dependencies away from it. Whoa, what a
ride! And I don’t know about you, but my neurons are like fried. We sure have
covered a lot of ground, haven’t we? We took a pleasant little stroll through the
y and theory of types, from its mathematical beginnings to its application
in computer science. And then we looked at Barbara Liskoff’s critical insight into
the definition of subtyping, that James Coplin called the Liskov Substitution
Principle. We walked through the old square rectangle dilemma, and we saw
what can go wrong when you violate the rule of representatives. We talked about
type checking, and then about design by contract. And then we looked at some
heuristics that can help you find and solvef the Liskov Substitution Principle.
Finally, we learned how to be prank called at 2 a.m. by an angry bunch of
programmers whom we’ve abused by violating the Liskov Substitution Principle.
5

Alright, well, that’s the end. It’s over. And I hope you learned something. I hope
you enjoyed yourself. But boy, do we have a lot more to talk about. And there’s
two solid principles left. And then there’s the component principles. bunch of
design patterns there’s agile practices there’s advanced test-drnt
you’re not gonna want to miss the next exciting episode of clean code episode
12 the interface segregation principle all right you girls you dogs let’s go come
on come on dogs girls ha ha grandchildren are the dessert of life Hwyl! Hwyl!
Hwyl! Hwyl! Hwyl! Hwyl! Hwyl! Hwyl! Hwyl! Hwyl! Hwyl! Hwyl! Hwyl!
Hwyl! We’ll be right back. We’ll be right back. We’ll see you next time.

6

You I’m going to go get some food. I’m going to drink a lot of water. Hi,
I’m Amanda. Hi, I’m Princess. Hi, Iâexis. Hi, I’m Luna. Welcome to
another episode of Clean Code. Clean Code. Clean Code. Clean Code. Your
master’s in the business. To begin a journey of. . . In this episode. . . Episode.
Episode. By Uncle Bob. Uncle Bob. Uncle Bob. Enjoy! Welcome, welcome to
episode 15, Solid Components. Here, let me take your hat. You remember the
previous episodes, episodes 8 through 14? design. Those principles included the
single responsibility principle, the open-closed principle, the Liskov substitution
principlee interface segregation principle, and the dependency inversion
principle. These were all principles about class design. They told us what
methods should go into classes and how the classes should depend upon each
other. Now, in this series larger scale entities made up of many classes. We’re
going to study the three principles of component cohesion, which tell us what
classes ought to go into a component. We’re also going to study the three
principles of component coupling, which tell us how componentsht to be
related to each other. And we’ll see the eerie connection between the solid
principles of class design and the that. We’re going to have to study white dwarf
stars and then we’re going to learn what components are and the roles they
play in design. Ten billion years from now the corpse of the Sun will be a white
dwarf star. An after the violence of its death throes. As I told you back in
episode 5, the burned-out remnant of our once great Sun will be roughly the
size of the earth and will retout half the Sun’s original mass. It’ll be
so dense that a teaspoon of this material will weigh several tons. But fueled
its exuberant youth. The nuclear reactions that supported it against its own
furious gravity ceased eons ago. But that leaves us with a question. What
fights that gravity now? After all, the gravity is still there, relentlessly trying to
pull that white dwarf in on itself. Back when it was a true star, it resisting it
now? Something must be, otherwise it would collapse. You might be ting
that the answer is obvious. It’s made of carbon. Carbon is solid. It’s the solid
carbon that’s resisting all that gravity. But if that’s what you were thinking,
you’re wrong. Solidity is merely a manifestation of the electromagnetic force.
For example, it is balls that makes them feel solid. OK, then, you say. It’s the
repulsion of the electrons in the outer shells of the carbon atoms that resists the
gravitational onslaught. But no. You see, the carbon atoms in a white dwarf
star have no elheir own. The temperatures at the time that the
white dwarf star normal atoms to exist. Indeed, this is a characteristic that the
white dwarf inherited from its parent star. The temperatures in the core are so
high that the electrons and protons are moving too fast to stick together. The
result is that the electrons form a kind of electronic fluid that flows between
between the nuclei of the carbon atoms in the white dwarf. These electrons form
a single system, and within a single system they must obey a rule called the
Pauli Exclusion Principle. In 1925, Wolfgang Pauli, in an attempt to explain
why the electrons within atoms organize Exclusion Principle, which says that
two electrons in the same system must not be in the same state. The state of
an electron can only differ in two ways, spin and energy. There are only two
spins, left and right. But there are many different possible energies. Since the
1

electronic fluid will arrange themselves into 10 to the 57th different energy levels.
10 to the 57th? That’s a big number! Some of those electrons must have very
high energies. The higher the energy of an electron, the faster that electron
moves. Since there are so many electrons in a white dwarf star, some of those
electrons must be moving very fast indeed. Curiosity creates a pressure and that
pressure resists gravity. Isn’t that weird? I mean it’s not the heat that resists
the crush of gravity. It’s the requirement that all the electrons have to be in
a different energy state. Cool. The pressure of e trapped in different
energy states by the Pauli Exclusion Principle degeneracy. Indeed, the matter
within a white dwarf star is said to be in a degenerate state. And that would
be the end of our story, except for one small detail. Though the carbon in a
white dwarf star is degenerate, it’s still carbon. And carbon under pressure
forms something that men life it will become an earth-sized diamond in the
sky. So just what is a component? Well to answer that question I’m gonna
have to tell you a story. I n my programming career in the late 60s using
machines like PDP-8s. We an assembler. At first, we just told the assembler
where the program was supposed to start. We’d put this origin statement into
the source code. You can see it here, it’s got a star in front of it. And that
told the assembler where the program was supposed to start. The assembler
would generate the absolute binary code, and then we’d load it into memory and
run it. A highly logical, if somewhat inflexible approach. As long as progrre small, less than a thousand lines or so, that inflexibility didn’t matter so
much, it was manageable. But over time, as programs grew in size, it became
a problem. Big programs usually include subroutine libraries. And that’s the
problem, because where are those subroutine libraries loaded? Let’s say that
we’ve got a program that starts at location 200. Let’s say that we also have
a subroutine library that begins at location 1200. That gives us about 1,000
locations for our program. What if youis longer than that? You could
always continue the program at address 2,000. subroutine library is longer than a
thousand instructions. The more subroutine libraries you use, the more complex
this issue becomes. I believe it could become rather annoying. Yeah, that would
be an understatement. Of course there was a simple solution to this. We could
keep all the subroutine libraries as source code and just append that source code
to the source code of our programs. Remember, this was in the days of paper,
tape, and punch cards. The computers were slow, compiling took a long time.
It took a long time just to read in all those cards from the card reader. And
besides, who wants to take a 5,000 card subroutine library and put it on the end
of a 300 card program? The source code solution just wasn’t very practical. code
without resolving the addresses. So that’s exactly what we did. We changed the
assemblers that they would emit relative addresses instead of absolute addresses
and then we changed the loaders so  you could tell them where to begin
loading and they would add that value to all the relative addresses. This was
great. binary decks and then we could stack those binary decks up on top of
each other and just load them. Uh, well, almost. Well, tarnation, son! How
in the name of horse apples are you gonna call a subroutine if you don’t know
where that subroutine’s loaded? Yeah, that was the problem. When everything’s
2

absolute, you can just call the subroutine But when everything’s relative, you
dw where anything is. Don’t those subroutines have names? Call them
by their names. And that’s exactly what we did. We changed the assemblers so
that they would emit external references for any name they couldn’t resolve, and
external definitions for any name they had defined. that it would link together
the external references to the external definitions. This worked great, except
for one thing. The more subroutine libraries we created, the longer the linking
process took. I worked on some systems whetook over 45 minutes to link
all the libraries together, and that’s just too long to wait when all you want to
do is load and run a program. process of linking by creating a new program
called the linker which resolved all the names adjusted all the relative addresses
and then emitted a single quick to load executable mmm and that is how we
came to create executable programs from independently relocatable modules
linked together by leaders This set the stage for the explosion of libraries and
languages th took place in the 70s. By the early 80s, we had moved from paper,
tape, and punch cards to disk. We kept everything on disk. We kept our source
files on disk. We kept our relocatable files on disk, our subroutine libraries,
and all our executables. files that we would run through the linkers and link
with subroutine libraries in order to create executable binaries that loaded very
quickly. Compiling a source code module into a relocatable binary usually didn’t
take more than a minute or two. But linking ndreds of modules together along
with dozens of subroutine libraries was often process requiring a half an hour
or more. And so it was the executable files that we deployed. And then in the
late 80s and early 90s we started using object-oriented languages. And with OO
came the potential for frameworks. Applications call subroutines. Frameworks
call applications. This inversion of calling order is important because to get it
you have to use the dependency inversion principle. The flow of control from
the framework to the application can’t be in the same direction as the source
code dependency which goes from the application to the framework. The source
code of the framework must never depend on the application. And so there
are two kinds of library. Framework libraries, from which control flows into
the application, and subroutine libraries, into which control will flow from the
application. And yet, the source code dependencies between the application
and these two libraries remain the same. but the librari know nothing at all
about the application. And we still had to link them libraries together using
them cods aren’t slow as molars as linkers. By the late 90s, memory had become
very plentiful and processor speeds had just gone through the roof. shrink
dramatically. Indeed, linker execution times diminished until they were nearly as
fast as load times. As a result, we started seeing new kinds of libraries. Shared
libraries in UNIX, dynamically linked libraries, DLLs, in Windows. You didn’t
have to link  these libraries, at least not right away. would just link them
for you. And that trend continues right up to the current day. Nowadays we
hardly ever use a separate linking step to link our executables together. We just
compile our source code into jar files or DLLs and then let the loader do all the
linking and relocating for us. And this leads us to the definition of a component.
A component is nothing more than an a gem, a jar file, or a shared library in
3

Unix. What does it mean to be independently deployable? It simply means
that a change to one does not cause others to be recompiled or redeployed. For
example, subroutine libraries are independently deployable, because I can change
the application without recompiling or redeploying the subroutine libraries.
is true of framework libraries. Changes to the application don’t require that
the framework component be recompiled or redeployed. The reason for the
independent deployability is the one-way relationship. Applications depend
on frameworks and subutine libraries. Frameworks and subroutine libraries
do not depend upon applications. And so the key to creating independently
deployable is to manage dependencies. DLLs and jar files that depend willy-nilly
all over the place cannot be independently deployed and are therefore not useful
components. But why is independent deployability so important? Well, wouldn’t
it be nice if we could make a change to our system or one jar file instead of
having to recompile and redeploy the whole system? Indeed, you shld be able
to hot-swap those components without bringing the system down. And wouldn’t
it be nice if the teams in your organization could work on their own components
independently without interfering with each other? development. And that’s
what this Clean Code series on components is all about. It’s about designing
systems of components that enjoy the maximum amount of independence. What
you have just heard was the opening statement by the counsel for the defense.
You are the judge, jury, and execut You will hear the a little jaunt through
the problem of making coffee. And so here is the design of the hardware of the
Mark IV coffee maker. I will be presenting to you the individual elements, their
purposes, and the way they work. horse hockey and just tell you the APRs
that you need to go. We begin with the boiler. Water is entered into the boiler
through some means we don’t care about right now. Notice the heating element
at the bottom. This heating element is under software control and it will be
tned on when we wish to boil the water to make coffee. set boiler function
with a true and when you need to turn the boiler off you’re gonna call it with a
false you got that son there is a sensor at the bottom of the boilers that detects
the presence of water it will tell you whether the boiler is empty or not now
what he means is that you can call this here get boiler water in that there boiler.
If it returns false, then they ain’t. Notice the siphon hose that goes from the
bottom of the boiler up out over the coffee filter holder. Then you turn on
the boiler heating element. It boils the water in the boiler. Steam builds up
inside the boiler and There ain’t nothing you need to do about this, because
once you turn on that concern boiler, well then that hot water is just gonna
spray out all over those coffee grounds. All you got to do is wait for that to
happen. There’s nothing else for you to do. As the hot water pours out over
the coffee grounds, it leaches the coffee compounds out of the coffee gro,
forming coffee. Then the coffee of the filter and collects in the pot. Boy I’ll
tell you that fella over there he just yep yep yep yep all the time he’s just a
windbag in it cuz there ain’t nothing here for you to do. That coffee is gonna
collect in that pot and all you gotta do is wait for it. Notice the warmer plate
that the pot sits upon. There’s a heating element in the plate that’s under the
software control. We to keep the coffee warm. Now I bet you’re just dying to
4

know how you’re t warmer on aren’t you? Well you do that by
calling this here set warmer function with a true and when you want to turn
the warmer off well you call that same there function with a false. There is a
pressure transducer at the The software can read this transducer to determine
the status of the coffee pot. Trans-ducer-schmans-fus-ser. It don’t matter one
donkey’s snout dribble what you call it, son. All you gotta know is this. You
call this here get plate function, it’s gonna return to you a one or tthree. A one means there ain’t no pot on that plate, son. ain’t got no coffee in
it and a three that means there’s a pot on their plate and there’s coffee in at
their pot. Now let us return to the boiler. There is a pressure relief valve up
at the top of the boiler. It’s under software control. When you open this valve
it relieves the steam pressure from the boiler and sometimes these kind-signed
executives get so doggone impatient for their coffee that they’re just gonna grab
that pot and pour  cup no matter what’s coming out of the spout
so what you gotta do son is this you gotta call this set valve function with a
true that’s gonna open the valve and stop that coffee from pouring out all over
the place making a mess bigger than button and this light. You can read the
status of the button from the software and the software can turn the light on
or off. This is how the user controls the coffee making process. Now what he
means is that you don’t start brewing coffee until this here get buttotion
returns a true and then when that boiler goes empty well then you call this set
light with a true that’ll And then when an empty pot goes back on the plate,
well then you call set light with a false to turn that light off. All right there
young’uns, you understand? You capiche, you savvy? I mean this here ain’t
rocket science, so now you go design that software to control this here coffee
maker. Now pause this video and take 30 minutes or so that will control the
coffee maker through this API. Amunderstand that you’ve summoned me
for the purpose of designing this trivial toy application? Why should I waste my
time on such nonsense? This is a simple exercise for the benefit of our audience.
It will not take much of your time and your cooperation would be Oh, very
well, since you insist. The accepted technique for decomposing requirements into
object-oriented designs is through noun-verb analysis. Indeed, I have heard of
this. Yes, well, we enumerate the nouns in the requirements and these nouns
beme candidate objects for our design. maker, warmer plate, boiler, valve,
heating element, sensor, button, and light. Logical. Clearly the coffee maker
noun represents the central object in our design. It is here that the high level
intelligence of the system resides. It is the coffee maker object that knows how
to sensors and two kinds of heating elements. The obvious conclusion is that
both have base classes. There must be a heating element base with derivatives,
one for the boiler element and one for the plate element. And there’s a sensor
base class, one for the boiler sensor and one for the plate sensor. I believe I see
where this is headed. Well, the rest is The boiler sensor, the boiler element, and
the valve both belong to the boiler. The boiler, the warmer, the light, and the
button all belong to the coffee maker. I see. As I said before, trivial. A problem
unworthy of my prodigious talents. So now if that will be all, I shall take my
leave of you, sir. Holder, please. moment if you’d be so kind pps you can
5

explain one or two points that I find puzzling oh very well if it will hasten the
end of this dissipation what message will the coffee makers send to the boiler in
order to open the valve clearly it will send the open valve message as I thought
and so what message boiler send to the valve object? Are you being purposely
obtuse, sir? The boiler will send the open message to the valve. Indeed, yes,
so it would. And so how then will the valve object implement that message?
You try my patience, sir, you and pass it a true indeed sir indeed but since the
coffee maker already knows it wants to open the valve why doesn’t it simply
call the appropriate api function why insert all these extra layers like the boiler
and the valve the question is absurd sir this is an object-oriented As astute an
observation as I have seen. But I have another question. I note that the heating
element base class has two derivatives, but no direct users. Correct, sir. That
base class forms the abstract foundation for many fferent kinds of heating
elements. Such abstraction is the very nature of object-oriented design. is clearly
impressive. But is there any code inside that base class? Of course, sir. It
contains the abstract methods turn on and turn off. And yet the boiler contains
the boiler element, the warmer contains the warmer element, neither of them
make polymorphic calls to the base class. So why is the base class there? The
base class represents the commonality between the two different derivatives. Are
you so ignorant of object-oriented design that you cannot see this? Apparently.
But then there is the sensor base class. What methods does it contain? This
line of questioning grows tedious beyond my ability to endure it, sir. It contains
one abstract method. And what, precisely, does that function return? It returns
the sensor status! Precisely what type does it return? An integer? An enum? A
string? Don’t trouble me with trivialities, sir. Such details are beneath me. I
am the architect, not the programmer. It’sndantly clear that you are not a
programmer. Quite. Will you grant me, sir, that the caller of GetSensorStatus
must know the type of the sensor he is calling, and therefore the call cannot be
polymorphic? Of course, sir. How could it be otherwise? Will you also grant
me that the majority of dependencies in your design point at concrete classes?
That is plainly obvious, sir. What is your point? Have you ever heard of the
term. . . solid? Eh? Eh? Solid, you say? Whatever do you mean? It is simply a
term I thought you might have recognized. Pay it no further mind. Allow me,
however, to point out that if you removed every class from that diagram except
for the coffee maker, the logic inside the coffee maker would remain substantially
unchanged. A few names would change and that is all. Every decision, every
bit of policy, every meaningful line of executable code remains in the coffee
maker class. In short, your design is farcical. It is not a design at all. All you
have done is to meaninglessly fill space with empty partitions in the name of
object-oriented design. But I am the architect! Ugh, a rumpf! Let’s try this
design again. And this time let’s apply the solid principles to the design. The
first step in any application design is to apply the single responsibility principle.
to properly partition the components, you need to determine who the actors are
so you can separate the responsibilities. So who are the actors in this problem?
Which groups of people will request changes to this system? It seems clear 
one of the actors is the person who decides to make coffee in the first place.
6

Right, let’s call this actor the brewer. This is the actor that’s interested in the
user interface and this actor will be requesting changes to the button and the
light. I like my coffee now. I refuse to wait for the pot to fill up. Okay, we’ll
call this actor the now drinker. so he can remove the pot from the plate when
the coffee’s still brewing. And I like my coffee hot! Ha ha ha ha ha ha ha ha
ha! Uh, sure. We’r call this actor the hot drinker because this actor is
interested in the temperature of the brewed coffee. Now son, you got yourself
three actors. And you remember that they’re single responsibility principle,
don’t you? So how many modules you think you’re gonna need? Well, at least
three, right? By the single responsibility principle, there ought to be at least
one module for each actor. The module for the brewer actor is pretty easy to
understand. It’s the one that controls the button and the lige Bob, you
have tripped the concretion alert. When designing the high level policy of a
system, it is customary to avoid mentioning the low level details of that system.
Ah, yes, good point, good point. at all about the low level Mark IV coffee maker
implementation. We’re going to avoid words like boiler, valve, heating element,
button, light, and sensor. Instead, we’ll describe the abstract purpose of these
components. So as I was saying, the module responsible to the brewer actor is
responsible for colling all the communications with the user. module. The
module responsible to the now drinker must allow that actor to get a coffee while
coffee is still being brewed. We don’t want a mess all over the place. We’re not
allowed to use the B and the V words here so we’ll call that module the hot water
source. An interesting choice of words It might as well be based on an infinite
supply of water, a microwave heater, and a pump. Both are software-controllable
sources of hot water. The module responsible  hot drinker must collect
the coffee and keep it hot. Now, we’re not allowed to use either of the P words
here, I have to say that containment vessel is an appropriate word. I like my
coffee strong enough to kill a Denebian slime devil. Okay, so now we’ve got our
three modules. the hot water source and the containment vessel. And now what
we’ve got to do is figure out what the relationship between all these modules
is. To do this we’re going to go up and down the abstraction layers like a yo-yo.
Weâo start with the yo-yo up because all of our modules are abstract.
They don’t know anything about the details of the Mark IV coffee maker. of
those modules we’re gonna throw the yo-yo down and we’re gonna look at how
the mark for coffee maker behaves we’ll use the mark for as a test case for
the behaviors of the abstract modules we start with the yo-yo up we’re at the
abstract level the brewer actor wants to start brewing coffee but now we throw
And down in the Mark IV that means that we’ve go detect that a
button has been pushed. But we’re not allowed to know about buttons, so the
yo-yo comes back up. And all we know is that the brewer actor sends the start
message to the UI. What should the UI do with this message? Well the obvious
answer is that it should tell the hot water source to start. No, you twit! have to
determine whether or not we’re already brewing. Second, you’ve got to know
whether there’s water in the boiler. Third, you’ve got to find out if there’s an
empty pot on thonly then can you tell the hot water source to start.
Ah yes, good point, good point. The UI is gonna have to remember whether or
7

not we already told it to start brewing and if we’re not already brewing then
source and the containment vessel if they’re ready and if they’re both ready then
it can tell the hot water source to start. This simple analysis has allowed us to
see that the UI and the hot water source both have a start method. It’s also
allowed us to see that the hot water source and the ent vessel both have
an are you ready method and finally it’s clear that the UI depends So, what
does the hot water source do when are you ready is called? Well, in the Mark
IV case, it’s going to make sure that the boiler’s got water in it. And by the
same token, the containment vessel in the Mark IV case is going to make sure
that there’s an empty pot on the plate. When start is called on the hot water
source, the Mark IV implementation needs to close the valve heating element.
And then the threatrol bubbles all the way back out to the brewer. What
happens to the threat of control after that? Well, we don’t know. Maybe there’s
some kind of operating system working behind the scenes. We’ll deal with that
later. The next event our Mark IV coffee maker has to deal with is when coffee
starts to drip into the pot the sensor on the warmer plate is going to switch
to pot not empty of course it’s the containment vessel that detects this but
then in the mark for the only action is to turn on the warm and since
that all happens down in the implementation well there’s nothing for us to do
at the abstract level the next event occurs when the now drinker removes the
partially brewed detected by the containment vessel but in this instance other
modules must be brought into play right but in the mark for case when the pots
removed what we need to do is open the valve but we’re not allowed to think
about valves and pots at the abstract level so instead we’ll have the containment
vessel tell the hot watece to suspend the flow by the same token when the
has returned to the plate, the valve must be closed again. At the abstract level,
this means that the containment vessel will send the resume message to the hot
water source. This nonsense of people taking the pot on and off the plate just
because they can’t be bothered to wait until the coffee is ready will continue
until the boiler is empty. At We’ll call that message done. The question is, who
sends it? Clearly in the Mark IV case, it’s the boiler tuld detect this
event. But the boiler is represented by the hot water source. But what if, in a
different kind of coffee maker, it were the containment vessel that detected that
it was full? vessel that would have to send the done message. Which module
sends the message is irrelevant. What matters is that the message gets sent.
This is a matter for the low-level implementation to work out and has nothing to
do with the high-level policy. Once the boiler is empty, people are still going to
be taking the pot while and we don’t want the containment vessel to be sending
send and resume messages to the hot water source during that time so if the
hot water source sends the done message to the UI it should also send it to the
containment vessel to let it know that brewing has completed at some point an
empty pot will be returned to the plate and that’s when the light should be
turned that detects that it’s got no more coffee to deliver so it’ll send the finished
message to the UI and that’s the high-level our coffee maker there are
three objects separated by responsibilities and they collaborate to brew coffee
what you see here is the high-level policy and lights and heating elements and
8

valves and all that stuff. Pure policy. Now that we have the high-level policy, we
need to implement the low-level details. This is where the open-close principle
comes in. We begin with the start message sent from the brewer actor to the UI.
Who really sends this message? Clearly, some function must call the getButton
function and check for true. Right. So, let’s say that there’s a derivative of the
UI. We’ll call it m4UI. And let’s give this derivative a poll method. Now, when
the poll method is called, it will call the getButton function of the API. what?
It’s true. It should start the brewing process. Sure, sure, but it’s the UI base
class that starts the brewing process. Remember, we had the UI send those
messages. Are you ready to the hot water source and to the containment vessel?
So we need some functionase class to do that. Let’s call that function
start. And we’ll have the pull method of the M4 UI call the start message in
the base class. Remember to make that method protected. Ah, good point,
good point. The only class that calls that start method in the UI is the M4 UI
derivative. So start should be protected. gonna deal with all those events there
bucko you’re gonna create yourself a derivative for each class and give each one
of them a pole method well I don’t see why not it seems perfectly re to
me each of the three base classes has its own derivative each of those derivatives
has a pole method that pole method calls protected methods in the base classes
when the events that So when the pot is removed from the plate, it’ll be the M4
containment vessel that actually detects that by calling the getPlate function.
And then it will call the protected method on the containment vessel base class
named stopFlow. Boiler in the API and then it’ll call the at capacity protected
method of the hot watource base class. But master who would put the pole
method on all these objects? Why Maine of course grasshopper. Maine will sit
in a hard loop calling the pole method of all three objects. And that pretty
much wraps which deal with the high-level policy of making coffee, each with
its own responsibility. We’ve got the three derivatives that implement all the
details of the Mark IV without making any policy decisions. And we’ve got
Maine that sits in a hard loop, divvying out calls to bowl. Logical, flasly
logical. An intriguing and apparently well-reasoned design. The evidence before
the court is incontrovertible. There’s no need for the jury to retire. You may. . .
Here is the design of our coffee maker. Now, watch this neat trick. See that red
line? Notice it contains all of the high-level policy classes of the coffee maker,
and all dependencies that cross that red line cross, going inwards in accordance
with the dependency inversion principle. The classes inside that red line make
our first componen Ja, und wat a fein komponent it is! high-level policy and
none of the low-level details. I think this component could be the heart of many,
many different coffee machines. Consider for example a coffee maker that has
an infinite supply of water heated with a small fusion reactor. The water is
pumped over coffee grounds and the coffee is collected into a tank with a spigot
at the bottom. coffee hot black yes the voice recognition unit would be the
UI the fusion generator and the pump would be the hot water source and the
tank and spigot would be the containment vessel this would work out quite well
why hell boys I think this component could be used to make hot chocolate or
chicken still right that’s kind of the point the m4 derivatives are plugins to this
9

component this component is completely isolated from them and knows nothing
about them better yet we could make all three of those derivatives their own
component they’re all independent and that would allow us to do something cool
and couple that to 6 containment vessel. I mean, think of the possibilities.
Complete interchangeability. Yes, interchangeability. Independent deployability.
The physical separation of high level policy from low level detail. These are the
benefits of good component design. You know you want it now, you know you
do. But what are the rules? How do you know what classes should go into a
component? And how do you know how to manage the dependencies between
those components? What are the principles of design that you should use? And
that is the topic of this series on the component principles. three principles of
component cohesion. These principles tell us which classes belong together in
a component and which classes should be kept in separate components. We’ll
continue this series by discussing the three principles of component coupling.
These principles tell us how to manage the dependencies between components
and what direction those dependencies should take. And we’ll a case study that’ll
show how to use all these princtogether in concert. And so the evidence has
been presented and the closing arguments have been made. And now you, the
jury, must deliberate. You’re not going to want to miss the next exciting episode
of Clean Code, episode 16, Component Cohesion. Done. guitar solo Thank you.
I’m going to go get some food. Let’s do two more. Okay. That’s good.

10


<end Transkript>

Start Question:
i

