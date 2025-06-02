# Tsuut'ina-English phrase translation
This repository provides a Python implementation of English phrase translation for Tsuut'ina (srs), mapping between inflected Tsuut'ina word forms and their nearest English translation equivalents.

When provided with (a) a Tsuut'ina lemma, (b) a set of grammatical features that specify a target inflected form of that lemma (defined as a series of tags, following the tagset used in lang-srs), (c) a set of conditions on acceptable subject and object forms of this lemma, and (d) an English translation 'template' appropriate to the target Tsuut'ina aspectual-modal form, this phrase translator returns a modified version of the English template that has been adapted to match the target Tsuut'ina form:

```
> eng_gen = EnglishGenerator()
> eng_gen.apply("itsiy", "+V+I+Ipfv+SbjSg4", "he/she/it is crying, he/she/it will cry")
'someone is crying, someone will cry'

# Adapt "he/she/it cried" to a second-person singular subject (+SbjSg2).
> eng_gen.apply("itsiy", "+V+I+Pfv+SbjSg2", "he/she/it cried")
'you cried'

# Adapt "he/she/it cries again and again" to a distributive 1PL subject (+SbjPl1+Distr).
> eng_gen.apply("itsiy", "+V+I+Ipfv+Rep+SbjPl1+Distr", "he/she/it cries again and again")
'each and every one of us cries again and again'
```

The above examples show the phrase translator adapting English translation templates that have been hand-crafted to reflect the meanings of specific tense-aspect-mode (TAM) forms (i.e., one translation template for Non-Past [`+Ipfv`] forms, another for Past [`+Pfv`] forms, etc.).  If English translation templates are not available for each unique TAM category, or if their meanings are predictable, this phrase translator can adapt a single English template string for the Non-Past (= imperfective) form to match the tense-aspect-mode category specified in the analysis:

```
> eng_gen.apply("didús", "+V+I+Ipfv+SbjSg1", "he/she/it will crawl")
'I will crawl'

# Non-Past English template, Past/+Pfv form requested for a dynamic verb ("event")
> eng_gen.apply("didús", "+V+I+Pfv+SbjSg1", "he/she/it will crawl", adjust_tense = "event")
'I crawled'

# Non-Past English template, Non-Past Repetitive form requested for a dynamic verb ("event")
> eng_gen.apply("didús", "+V+I+Prog+SbjPl3+Distr", "he/she/it will crawl", adjust_tense = "event")
'each and every one of them crawls again and again'
```

# Licenses
This project is released under an Apache License 2.0, mirroring the license used by [UAlbertaALTLab/morphodict](https://github.com/UAlbertaALTLab/morphodict/).  It relies on parts of the `inflect` module from the web mining module [Pattern](https://github.com/clips/pattern/) for inflecting English translation templates, which was made available under a [three-clause BSD license](https://github.com/clips/pattern/blob/master/LICENSE.txt) that is copyright (c) 2011-2013 University of Antwerp, Belgium.
