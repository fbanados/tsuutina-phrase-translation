#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Given a Tsuut'ina lemma; a set of tags from the Tsuut'ina FST describing a
# particular inflection; and, for English phrase translations, a set of 'sense'
# strings (typically drawn from the entries in the lemma database for this
# lexcial item) and conditions on acceptable subjects, direct objects, and
# indirect objects for this lemma; produce well-formed Tsuut'ina wordforms
# and English free translations for the intended inflection.
#
# Usage:
# 
#   srs_gen = TsuutinaGenerator()
#   eng_gen = EnglishGenerator()
#
#   srs_gen.apply('itsiy', '+V+I+Ipfv+SbjSg4')
#       ==> "ts'itsiy"
#
#   eng_gen.apply('itsiy', '+V+I+Ipfv+SbjSg4', \
#                 'he/she/it is crying, he/she/it will cry')
#       ==> 'someone is crying, someone will cry'
#

# TODO:
#
#   * Finish implementing the logic for distributives in ditransitives!
#
#   * Test objects! (esp. DObjIndef, which is most urgently needed right now;
#     then regular objects, then reciprocals and reflexives)
#
#   * Finish adding all of the currently-implemented suffixes and enclitics
#

import csv
import re
import sys

import foma

# Import parts of the 'pattern' module (https://github.com/clips/pattern/) to
# help inflect and lemmatize English verbs.
import inflect.inflect as infl

# Work-around for iterator-related bug in 'pattern'.  The first time 'lexeme'
# (or any similar method) is called, it throws an exception, but later calls
# are then fine (since lazy-loading has then taken place).  See:
#
# https://github.com/RaRe-Technologies/gensim/issues/2438#issuecomment-841624827
try:
    infl.lexeme('gave')
except:
    pass


class TsuutinaGenerator(object):
    def __init__(self, fomabin = 'lexdb-verbs.fomabin'):
        # Load the FST using foma(1)'s Python bindings.
        #
        # (These are *much* slower than what the 'fst-lookup' Python package
        # provides, but 'fst-lookup' unfortunately isn't able to work with
        # 'srs2crk2eng-verbs.fomabin'.  If we need a work-around, we might be
        # able to call 'flookup -x -i -b $FOMABIN' as a subprocess, pipe the
        # items we need to it, and read its output back in below.  For now,
        # though, this works well enough.)
        self._fst = foma.FST.load(fomabin)

    def apply(self, headword, tags):
        # headword = 'itsiy', tags = '+V+I+...'
        return sorted(list(self._fst.apply_down(headword + tags)))


class EnglishGenerator(object):
    # (fst_string, sbj_pl_only, is_distrib, gender_3sg) =>
    #   (eng_sbj_form, eng_sbj_person, eng_sbj_num, eng_refl_form)
    #
    # Note that the colloquial English equivalents of distributive plurals
    # involving reflexive objects are wonky:
    #
    #   * The verbs inflect with 3SG subject forms ("each and every one of
    #     us eat_s_ lunch at noon", rather than *"each and every one of us
    #     eat lunch at noon"), but
    #
    #   * The appropriate reflexive pronoun matches the subject in person
    #     and number, not 3SG ("each and every one of us sees _ourselves_
    #     as important", not ?"each and every one of us sees himself/
    #     herself/itself as important" [which may be OK, but wouldn't be
    #     what I'd use by default]).
    #
    # The following dictionary's values catch these cases by specifying the
    # appropriate subject-number inflection and reflexive form, making sure
    # that we get "sees ourselves", etc. when they are needed.
    _fst_sbj_to_eng_sbj = {
        ('SbjSg1', False, False, None):  ('I', 1, infl.SG, 'myself'),
        ('SbjSg1', False, True, None):   ('I', 1, infl.SG, 'myself'),
        ('SbjSg1', True, False, None):   ('I', 1, infl.SG, 'myself'),
        ('SbjSg1', True, True, None):    ('I', 1, infl.SG, 'myself'),

        ('SbjSg2', False, False, None):  ('you', 2, infl.SG, 'yourself'),
        ('SbjSg2', False, True, None):   ('you', 2, infl.SG, 'yourself'),
        ('SbjSg2', True, False, None):   ('you', 2, infl.SG, 'yourself'),
        ('SbjSg2', True, True, None):    ('you', 2, infl.SG, 'yourself'),

        ('SbjSg3', False, False, None):  ('he/she/it', 3, infl.SG, \
                                          'himself/herself/itself'),
        ('SbjSg3', False, False, 'm'):   ('he', 3, infl.SG, 'himself'),
        ('SbjSg3', False, False, 'f'):   ('she', 3, infl.SG, 'herself'),
        ('SbjSg3', False, False, 'n'):   ('it', 3, infl.SG, 'itself'),
        ('SbjSg3', False, False, 'mf'):  ('he/she', 3, infl.SG, \
                                          'himself/herself'),
        ('SbjSg3', False, True, None):   ('he/she/it', 3, infl.SG, \
                                          'himself/herself/itself'),
        ('SbjSg3', False, True, 'm'):    ('he', 3, infl.SG, 'himself'),
        ('SbjSg3', False, True, 'f'):    ('she', 3, infl.SG, 'herself'),
        ('SbjSg3', False, True, 'n'):    ('it', 3, infl.SG, 'itself'),
        ('SbjSg3', False, True, 'mf'):   ('he/she', 3, infl.SG, \
                                          'himself/herself'),
        ('SbjSg3', True, False, None):   ('he/she/it', 3, infl.SG, \
                                          'himself/herself/itself'),
        ('SbjSg3', True, False, 'm'):    ('he', 3, infl.SG, 'himself'),
        ('SbjSg3', True, False, 'f'):    ('she', 3, infl.SG, 'herself'),
        ('SbjSg3', True, False, 'n'):    ('it', 3, infl.SG, 'itself'),
        ('SbjSg3', True, False, 'mf'):   ('he/she', 3, infl.SG, \
                                          'himself/herself'),
        ('SbjSg3', True, True, None):    ('he/she/it', 3, infl.SG, \
                                          'himself/herself/itself'),
        ('SbjSg3', True, True, 'm'):     ('he', 3, infl.SG, 'himself'),
        ('SbjSg3', True, True, 'f'):     ('she', 3, infl.SG, 'herself'),
        ('SbjSg3', True, True, 'n'):     ('it', 3, infl.SG, 'itself'),
        ('SbjSg3', True, True, 'mf'):    ('he/she', 3, infl.SG, \
                                          'himself/herself'),

        ('SbjSg4', False, False, None):  ('someone', 3, infl.SG, 'themself'),
        ('SbjSg4', False, True, None):   ('each and every one', 3, infl.SG, \
                                          'themselves'),
        ('SbjSg4', True, False, None):   ('someone (pl.)', 3, infl.SG, \
                                          'themselves'),
        ('SbjSg4', True, True, None):    ('each and every one', 3, infl.SG, \
                                          'themselves'),

        ('SbjPl1', False, False, None):  ('we both', 1, infl.PL, 'ourselves'),
        ('SbjPl1', False, True, None):   ('each and every one of us', \
                                           3, infl.SG, 'ourselves'),
        ('SbjPl1', True, False, None):   ('we all', 1, infl.PL, 'ourselves'),
        ('SbjPl1', True, True, None):    ('each and every one of us', \
                                           3, infl.SG, 'ourselves'),

        ('SbjPl2', False, False, None):  ('you both', 2, infl.PL, \
                                          'yourselves'),
        ('SbjPl2', False, True, None):   ('each and every one of you', \
                                           3, infl.SG, 'yourselves'),
        ('SbjPl2', True, False, None):   ('you all', 2, infl.PL, \
                                          'yourselves'),
        ('SbjPl2', True, True, None):    ('each and every one of you', \
                                           3, infl.SG, 'yourselves'),

        ('SbjPl3', False, False, None):  ('they both', 3, infl.PL, \
                                          'themselves'),
        ('SbjPl3', False, True, None):   ('each and every one of them', \
                                           3, infl.SG, 'themselves'),
        ('SbjPl3', True, False, None):   ('they all', 3, infl.PL, \
                                          'themselves'),
        ('SbjPl3', True, True, None):    ('each and every one of them', \
                                           3, infl.SG, 'themselves')
    }

    # eng_sbj => (fst_sbj, gender_3sg) [e.g., "she": ('SbjSg3', 'f')]
    _eng_sbj_to_fst_sbj_and_gender = dict([
        (eng_sbj, (fst_sbj, gender)) for \
            (fst_sbj, _, _, gender), (eng_sbj, _, _, _) in \
            _fst_sbj_to_eng_sbj.items()
    ])

    # (fst_pers_num, gender_3sg) => eng_poss_form
    _fst_person_number_to_eng_poss = {
        ('Sg1', None):   'my',
        ('Sg2', None):   'your',
        ('Sg3', None):   'his/her/its',
        ('Sg3', 'm'):    'his',
        ('Sg3', 'f'):    'her',
        ('Sg3', 'n'):    'its',
        ('Sg3', 'mf'):   'his/her',
        ('Sg4', None):   'their',
        ('Pl1', None):   'our',
        ('Pl2', None):   'your',
        ('Pl3', None):   'their',
        ('Areal', None): 'its',
        ('Refl', None):  'SELF',
        ('Recip', None): 'each others\'',
        ('Indef', None): 'its',
        ('Given', None): 'GIVEN',
    }

    # (fst_string, is_distrib, gender_3sg) =>
    #   (eng_obj_form, eng_obj_person, eng_obj_num)
    _fst_obj_to_eng_obj = {
        ('ObjSg1', True, None):    ('me', 1, infl.SG),
        ('ObjSg1', False, None):   ('me', 1, infl.SG),

        ('ObjSg2', True, None):    ('you', 2, infl.SG),
        ('ObjSg2', False, None):   ('you', 2, infl.SG),

        ('ObjSg3', True, None):    ('him/her/it', 3, infl.SG),
        ('ObjSg3', True, 'm'):     ('him', 3, infl.SG),
        ('ObjSg3', True, 'f'):     ('her', 3, infl.SG),
        ('ObjSg3', True, 'n'):     ('it', 3, infl.SG),
        ('ObjSg3', True, 'mf'):    ('him/her', 3, infl.SG),
        ('ObjSg3', False, None):   ('him/her/it', 3, infl.SG),
        ('ObjSg3', False, 'm'):    ('him', 3, infl.SG),
        ('ObjSg3', False, 'f'):    ('her', 3, infl.SG),
        ('ObjSg3', False, 'n'):    ('it', 3, infl.SG),
        ('ObjSg3', False, 'mf'):   ('him/her', 3, infl.SG),

        ('ObjSg4', True, None):    ('each and every one of someone (pl.)', \
                                     3, infl.SG),
        ('ObjSg4', False, None):   ('someone', 3, infl.SG),

        ('ObjPl1', True, None):    ('each and every one of us', 3, infl.SG),
        ('ObjPl1', False, None):   ('us', 1, infl.PL),

        ('ObjPl2', True, None):    ('each and every one of you', 3, infl.SG),
        ('ObjPl2', False, None):   ('you (pl.)', 2, infl.PL),

        ('ObjPl3', True, None):    ('each and every one of them', 3, infl.SG),
        ('ObjPl3', False, None):   ('them', 3, infl.PL),

        ('ObjRecip', True, None):  ('each and every one of each other', \
                                     None, None),
        ('ObjRecip', False, None): ('each other', None, None),

        ('ObjRefl', True, None):   ('self', None, None),
        ('ObjRefl', False, None):  ('self', None, None),

        ('ObjIndef', True, None):  ('each and every one of something', \
                                     3, infl.SG),
        ('ObjIndef', False, None): ('something', 3, infl.SG),

        ('ObjAreal', True, None):  ('each and every one of them '\
                                    '(places/spaces)', 3, infl.SG),
        ('ObjAreal', False, None): ('it (place/space)', 3, infl.SG),
    }

    def _to_english_subjects(self, fst_sbj, sbj_pl_only, distrib, \
                             gender_3sg = None):
        return self._fst_sbj_to_eng_sbj[\
            (fst_sbj, sbj_pl_only, distrib, gender_3sg)]

    def _to_english_objects(self, fst_obj, sbj_form, sbj_person, sbj_number, \
                            sbj_refl, distrib, gender_3sg = None):
        fst_obj = fst_obj[1:]
        (obj_form, obj_person, obj_number) = \
            self._fst_obj_to_eng_obj[(fst_obj, distrib, gender_3sg)]

        if 'self' in obj_form:
            obj_form = sbj_refl
        elif 'each other' in obj_form:
            (obj_person, obj_number) = (sbj_person, sbj_number)

        return (obj_form, obj_person, obj_number)

    def _takes_distrib(self, s):
# TODO: Temporarily comment out 'Indef' (to pare down the number of interpre-
# tations of distributive plurals that appear in the output for now)
#        return 'Pl' in s or 'Sg4' in s or 'Areal' in s or 'Indef' in s
        return 'Pl' in s or 'Sg4' in s or 'Areal' in s

    def _sbj_and_objs_to_dict(self, sbj, dobj = None, iobj = None):
        results = {'SbjForm': sbj[0], 'SbjPerson': sbj[1], \
                   'SbjNumber': sbj[2], 'SbjRefl': sbj[3] }
        if dobj:
            results |= \
                {'DObjForm': dobj[0], 'DObjPerson': dobj[1], \
                 'DObjNumber': dobj[2]}
        if iobj:
            results |= \
                {'IObjForm': iobj[0], 'IObjPerson': iobj[1], \
                 'IObjNumber': iobj[2]}

        return results

    # Convert participant-related FST tags into nearest equivalent English
    # forms and person/number values.
    def _to_english_participants(self, argument_structure, fst_sbj, \
        fst_dobj = None, fst_iobj = None, sbj_pl_only = False, \
        distrib = False, fst_rest = []):

        if argument_structure == 'Im':
            return [{'SbjForm': 'it', 'SbjPerson': 3, \
                'SbjNumber': infl.SG}]

        elif argument_structure == 'I':
            (sbj_form, sbj_person, sbj_number, sbj_refl) = \
                self._to_english_subjects(fst_sbj, sbj_pl_only, distrib)
            return [{'SbjForm': sbj_form, 'SbjPerson': sbj_person, \
                'SbjNumber': sbj_number, 'SbjRefl': sbj_refl}]

        elif argument_structure == 'DE':
            # For direct object experiencer verbs, the equivalent of the
            # subject in English is expressed through direct object morph-
            # ology in Tsuut'ina.  By mapping from those direct object
            # tags onto the equivalent subject tags, we can re-use the
            # subject forms defined above.
            (sbj_form, sbj_person, sbj_number, sbj_refl) = \
                self._to_english_subjects(fst_dobj.replace('DObj', \
                'Sbj'), sbj_pl_only, distrib)
            return [{'SbjForm': sbj_form, 'SbjPerson': sbj_person, \
                'SbjNumber': sbj_number, 'SbjRefl': sbj_refl}]

        elif argument_structure == 'OE':
            # Likewise, but for indirect object experiencer verbs, where
            # indirect object morphology expresses the equivalent of the
            # subject in English.
            (sbj_form, sbj_person, sbj_number, sbj_refl) = \
                self._to_english_subjects(fst_iobj.replace('IObj', \
                'Sbj'), sbj_pl_only, distrib)
            return [{'SbjForm': sbj_form, 'SbjPerson': sbj_person, \
                'SbjNumber': sbj_number, 'SbjRefl': sbj_refl}]

        elif argument_structure == 'T':
            # If this is distributive, then things get a little more compli-
            # cated, since distributive marking can refer either to the
            # subject, the object, or both.  We therefore return different
            # sets of subject and object forms to reflect all possible
            # interpretations.
            sbj_distrib = self._takes_distrib(fst_sbj)
            obj_distrib = self._takes_distrib(fst_dobj)

            # Leave -ná human plural nominalizations out of this: their
            # interpretation is handled further on below.
            if distrib and not 'NomzPl' in fst_rest:
                # If both the subject and the object could be interpreted
                # as distributive plurals, we need to return (a) the sub-
                # ject distributive reading, (b) the object distributive
                # reading, and (c) the reading where both subject and
                # object are distributive.
                if sbj_distrib and obj_distrib:
                    # A. Subject interpreted as distributive, object not.
                    results = []
                    sbj = self._to_english_subjects(fst_sbj, sbj_pl_only, True)
                    results.append(self._sbj_and_objs_to_dict(sbj, \
                        dobj = self._to_english_objects(fst_dobj, \
                            *sbj, False)))

                    # B. Object interpreted as distributive, subject not.
                    sbj = self._to_english_subjects(fst_sbj, sbj_pl_only, False)
                    results.append(self._sbj_and_objs_to_dict(sbj, \
                        dobj = self._to_english_objects(fst_dobj, \
                            *sbj, True)))

                    # C. Both subject and object interpreted as distrib.
                    sbj = self._to_english_subjects(fst_sbj, sbj_pl_only, True)
                    results.append(self._sbj_and_objs_to_dict(sbj, \
                        dobj = self._to_english_objects(fst_dobj, \
                            *sbj, True)))

                    return results

            # Otherwise, if this isn't a distributive form or distribu-
            # tivity could only refer here to either the subject or the
            # object, just return a single set of subject and object
            # forms/values.
            sbj = self._to_english_subjects(fst_sbj, sbj_pl_only, \
                distrib and sbj_distrib)
            return [self._sbj_and_objs_to_dict(sbj, dobj = \
                self._to_english_objects(fst_dobj, *sbj, \
                distrib and obj_distrib))]

        elif argument_structure == 'O':
            # Same logic as above, but for indirect (oblique) objects.
            sbj_distrib = self._takes_distrib(fst_sbj)
            obj_distrib = self._takes_distrib(fst_iobj)
            if distrib and not 'NomzPl' in fst_rest:
                # If both the subject and the object could be interpreted
                # as distributive plurals, we need to return (a) the sub-
                # ject distributive reading, (b) the object distributive
                # reading, and (c) the reading where both subject and
                # object are distributive.
                if sbj_distrib and obj_distrib:
                    # A. Subject interpreted as distributive, object not.
                    results = []
                    sbj = self._to_english_subjects(fst_sbj, sbj_pl_only, True)
                    results.append(self._sbj_and_objs_to_dict(sbj, \
                        iobj = self._to_english_objects(fst_iobj, \
                            *sbj, False)))

                    # B. Object interpreted as distributive, subject not.
                    sbj = self._to_english_subjects(fst_sbj, sbj_pl_only, False)
                    results.append(self._sbj_and_objs_to_dict(sbj, \
                        iobj = self._to_english_objects(fst_iobj, \
                            *sbj, True)))

                    # C. Both subject and object interpreted as distrib.
                    sbj = self._to_english_subjects(fst_sbj, sbj_pl_only, True)
                    results.append(self._sbj_and_objs_to_dict(sbj, \
                        iobj = self._to_english_objects(fst_iobj, \
                            *sbj, True)))

                    return results

            # Otherwise, if this isn't a distributive form or distribu-
            # tivity only refers here to either the subject or the object,
            # just return a single set of subject and object forms/values.
            sbj = self._to_english_subjects(fst_sbj, sbj_pl_only, \
                distrib and sbj_distrib)
            return [self._sbj_and_objs_to_dict(sbj, iobj = \
                self._to_english_objects(fst_iobj, *sbj, \
                distrib and obj_distrib))]

        elif argument_structure == 'D':
            if not distrib:
                (sbj_form, sbj_person, sbj_number, sbj_refl) = \
                    self._to_english_subjects(fst_sbj, sbj_pl_only, distrib)

                (dobj_form, dobj_person, dobj_number) = \
                    self._to_english_objects(fst_dobj, \
                    sbj_form, sbj_person, sbj_number, sbj_refl, distrib)

                (iobj_form, iobj_person, iobj_number) = \
                    self._to_english_objects(fst_iobj, \
                    sbj_form, sbj_person, sbj_number, sbj_refl, distrib)

                return [{'SbjForm': sbj_form, 'SbjPerson': sbj_person, \
                    'SbjNumber': sbj_number, 'SbjRefl': sbj_refl, \
                    'DObjForm': dobj_form, 'DObjPerson': dobj_person, \
                    'DObjNumber': dobj_number, \
                    'IObjForm': iobj_form, 'IObjPerson': iobj_person, \
                    'IObjNumber': iobj_number}]

            # Handle distributives.
            return []   # FIXME

    def _paradigm_to_aspect(self, paradigm_name):
        aspect = paradigm_name
        if aspect.endswith('-REP'):
            aspect = aspect[0:aspect.rfind('-')]
            aspect = aspect[aspect.rfind('-') + 1:] + '-REP'
        elif aspect.endswith('-REPC'):
            aspect = aspect[0:aspect.rfind('-')]
            aspect = aspect[aspect.rfind('-') + 1:] + '-REPC'
        else:
            aspect = aspect[aspect.rfind('-') + 1:]

        return aspect

    def apply(self, headword, tags, senses = None, sbj_conditions = None, \
        dobj_conditions = None, iobj_conditions = None, adjust_tense = None, \
        expand_placeholders = False):
        # headword = 'itsiy', tags = '+V+I+...' (same tags as in Tsuut'ina
        # generator class above), senses = 'English subsense 1 of sense 1,
        # English subsense 2 of sense 1; English subsense 1 of sense 2'
        #
        # By default, this method assumes that the English phrases being
        # returned should match the given sense strings in their tense (unless
        # a suffix/enclitic like the delayed future is present and requires
        # some additional changes in wording).  If 'adjust_tense' is
        # specified (either 'event' or 'state'), it is assumed that the sense
        # strings refer to Non-Past meanings (e.g., "he/she/it will do X / is
        # doing X / Xes"), and that verbs in the resulting English phrases
        # should be modified to reflect the aspect specified in 'tags'.

        # If we haven't been given any sense strings for this lemma, bail out
        # now.
        if not senses:
            return ''

        # Parse the FST tag string (e.g., "itsiy+V+I+Ipfv+SbjSg3+Distr" -->
        # ['itsiy', 'V', 'I', 'Ipfv', 'SbjSg3', ['Distr']]).
        fst_tags = headword + tags
        (fst_lemma, fst_pos, fst_arg, fst_aspect, *fst_rest) = \
            fst_tags.split('+')

        # If this is a verb form that takes a fixed reflexive object, then
        # we need to make sure that previous data pre-processing scripts
        # (in particular, those used to expand the temporary paradigm
        # database into the full lemma database format, which involves
        # re-inflecting a number of forms) didn't accidentally change the
        # placeholder "self" into an expanded form.  If it did, change it
        # back now.
        if 'DObjRefl' in fst_rest or 'IObjRefl' in fst_rest:
            senses = re.sub(r'(himself/herself/itself|himself/herself|'\
                r'himself|herself|itself)', 'self', senses)

        # If this is a repetitive verb form, make sure that the appropriate
        # suffix is added onto the aspect label (and that the whole string is
        # converted to upper case, so that it matches the capitalization
        # conventions used in the lemma database, e.g., FST '+Ipfv+Rep' ==
        # 'IPFV-REP' in the lemma database)
        if 'Rep' in fst_rest:
            fst_aspect = fst_aspect + '-REP'
        elif 'RepC' in fst_rest:
            fst_aspect = fst_aspect + '-REPC'
        fst_aspect = fst_aspect.upper()

        # Is this a distributive plural form?
        is_distributive = 'Distr' in fst_rest

        # Does this lemma (generally) only appear with plural subjects?
        # (Needed to distinguish between, e.g., "all of us" (plural only)
        # and "both of us" (not plural-only) in non-distributive cases)
        is_sbj_pl_only = sbj_conditions == 'SubjPl'

        # Fish out all of the subject and object markers that are present
        # among the remaining tags.
        fst_sbj = None
        if fst_sbjs := [t for t in fst_rest if t.startswith('Sbj')]:
            fst_sbj = fst_sbjs[0]
        fst_dobj = None
        if fst_dobjs := [t for t in fst_rest if t.startswith('DObj')]:
            fst_dobj = fst_dobjs[0]
        fst_iobj = None
        if fst_iobjs := [t for t in fst_rest if t.startswith('IObj')]:
            fst_iobj = fst_iobjs[0]

        # Refine the 'E'(xperiencer) argument structure class to specify
        # whether object marking appears on direct or indirect objects.
        if fst_arg == 'E':
            if fst_dobj:
                fst_arg = 'DE'
            elif fst_iobj:
                fst_arg = 'OE'

        # Split the given sense string into a list of senses and embedded
        # lists of subsenses, e.g.,
        #
        #   "he/she/it will catch him/her/it; he/she/it will trap it,
        #    he/she/it will catch it in a trap" ==>
        #   [["he/she/it will catch him/her/it"],
        #    ["he/she/it will trap it", "he/she/it will catch it in a trap"]]
        senses_and_subsenses = [s.split(', ') for s in senses.split('; ')]

        # Process each of the given sense strings for this aspect.
        english_senses = []
        for sense_group in senses_and_subsenses:
            # Store English phrase translations of subsenses of the current 
            # current sense in 'english'.
            english = []
            english_senses.append(english)

            for sense in sense_group:
                eng_match = re.match(\
                    r'(he|she|it|he\/she|he\/she\/it|they both|they all)'\
                    r'\s+([^ ]+)(.*)', sense)
                if not eng_match:
                    continue

                # Get the form that the subject takes in English here, as well
                # as its gender ('m', 'f', 'mf', or 'n' for 3SG, or None for
                # all subject person-number combinations).
                eng_sbj_form = eng_match.group(1)
                _, eng_sbj_gender = \
                    self._eng_sbj_to_fst_sbj_and_gender[eng_sbj_form]

                eng_verb = eng_match.group(2)
                original_after_verb = eng_match.group(3).strip()

                # Get the form, person, and number of the English translation
                # equivalent of the participants specified in the FST tags
                # (taking different argument structures and distributive
                # plurals into account).
                participant_options = self._to_english_participants(fst_arg, \
                    fst_sbj, fst_dobj, fst_iobj, is_sbj_pl_only, \
                    is_distributive, fst_rest)
                for participants in participant_options:
                    sbj_form = participants['SbjForm']
                    sbj_person = participants['SbjPerson']
                    sbj_number = participants['SbjNumber']

                    after_verb = original_after_verb

                    # If the placeholder "self's" is present in this sense,
                    # replace it with the appropriate English possessive
                    # pronoun that is corefential with the subject.
                    if expand_placeholders and "self's" in after_verb:
                        sbj_pers_num = fst_sbj.removeprefix('Sbj')
                        if fst_arg == 'DE':
                            sbj_pers_num = fst_dobj.removeprefix('DObj')
                        elif fst_arg == 'OE':
                            sbj_pers_num = fst_iobj.removeprefix('IObj')

                        poss_pron = \
                            self._fst_person_number_to_eng_poss[\
                            (sbj_pers_num, eng_sbj_gender)]
                        if poss_pron:
                            after_verb = after_verb.replace("self's", \
                                poss_pron)

                    # Similarly, if the placeholder "self" is present in this
                    # sense (and hasn't already been turned into the appro-
                    # priate reflexive pronoun, which should have happened by
                    # this point for argument structures involving a subject
                    # and a direct/indirect object), replace it with the
                    # matching English reflexive pronoun that is coreferential
                    # with the subject.
                    elif expand_placeholders and "self" in after_verb:
                        if fst_arg in ['Im', 'I', 'DE', 'OE']:
                            after_verb = after_verb.replace("self", \
                                participants['SbjRefl'])

                    # If we've been asked to, adjust the tense of the lexical
                    # verb in this sense string to match the semantics of the
                    # aspect specified in the tags.  (No adjustments are done
                    # to sense strings for Non-Past verb phrases, since this
                    # assumes that sense strings for 'adjust_tense' already
                    # reflect Non-Past meanings)
                    if adjust_tense and fst_aspect != 'IPFV':
                        # Get the lemma of the lexical verb in this sense
                        # string.
                        if eng_verb in ['will', 'is', 'are', 'was', 'were', \
                                        'may', 'might']:
                            after_verb_parts = after_verb.split(' ')

                            # Dynamic verbs involving the construction "be
                            # about to V": "I am about to be dreaming" -->
                            # "I am about to be dreaming"
                            if adjust_tense == 'event' and \
                               (after_verb.startswith('about to') or \
                                after_verb.startswith('just about to') or \
                                after_verb.startswith('just about')):
                                eng_verb = infl.conjugate('be', \
                                    infl.PRESENT, \
                                    person = sbj_person, \
                                    number = sbj_number)
                            # All other dynamic verbs: "I will eat" --> "I
                            # eat", "I am sitting" --> "I sit"
                            elif adjust_tense == 'event':
                                eng_verb = infl.conjugate(\
                                    infl.lemma(after_verb_parts[0]), \
                                    infl.PRESENT, \
                                    person = sbj_person, \
                                    number = sbj_number)
                                after_verb = ' '.join(after_verb_parts[1:])
                            # Stative verbs: "I am sitting" --> "I am sitting"
                            else:
                                if eng_verb == 'will' and \
                                   after_verb_parts[0] == 'be':
                                    eng_verb = infl.conjugate('be', \
                                        infl.PRESENT, \
                                        person = sbj_person, \
                                        number = sbj_number)
                                    after_verb = ' '.join(after_verb_parts[1:])
                        else:
                            eng_verb = infl.lemma(eng_verb)

                        # Adjust the inflected English verb to more closely
                        # reflect the meaning of the corresponding Tsuut'ina
                        # aspect.
                        if fst_aspect == 'PFV':
                            # "he/she/it eats" --> "he/she/it ate"
                            eng_verb = infl.conjugate(eng_verb, infl.PAST, \
                                person = sbj_person, number = sbj_number)
                        elif fst_aspect == 'PROG' and not \
                            (after_verb.startswith("about to") or
                             after_verb.startswith('just about to') or \
                             after_verb.startswith('just about')):
                            # "he/she/it eats" --> "he/she/it is eating";
                            # "he/she/it is about to be dreaming" -->
                            # "he/she/it is about to be dreaming" (= leave
                            # "BE about to" Progressives unchanged).
                            be_verb = infl.conjugate("be", infl.PRESENT, \
                                person = sbj_person, number = sbj_number)
                            pres_part_eng_verb = infl.conjugate(eng_verb, \
                                infl.PRESENT, aspect = infl.PROGRESSIVE, \
                                person = sbj_person, number = sbj_number)

                            eng_verb = be_verb
                            after_verb = f"{pres_part_eng_verb} {after_verb}"
                        elif fst_aspect == 'POT':
                            # "he/she/it eats" --> "he/she/it might eat"
                            after_verb = f"{infl.lemma(eng_verb)} {after_verb}"
                            eng_verb = "might"
                        elif fst_aspect == 'IPFV-REP':
                            # "he/she/it eats" --> "he/she/it eats again and
                            # again"
                            if "again and again" not in after_verb:
                                after_verb += " again and again"
                        elif fst_aspect == 'IPFV-REPC':
                            # "he/she/it eats" --> "he/she/it keeps eating"
                            pres_part_eng_verb = infl.conjugate(eng_verb, \
                                infl.PRESENT, aspect = infl.PROGRESSIVE, \
                                person = sbj_person, number = sbj_number)
                            keep_verb = infl.conjugate("keep", infl.PRESENT, \
                                person = sbj_person, number = sbj_number)

                            eng_verb = keep_verb
                            after_verb = f"{pres_part_eng_verb} {after_verb}"
                        elif fst_aspect == 'PFV-REP':
                            # "he/she/it eats" --> "he/she/it ate again and
                            # again"
                            eng_verb = infl.conjugate(eng_verb, infl.PAST, \
                                person = sbj_person, number = sbj_number)

                            if "again and again" not in after_verb:
                                after_verb = f"{after_verb} again and again"
                        elif fst_aspect == 'PFV-REPC':
                            # "he/she/it eats" --> "he/she/it kept eating"
                            pres_part_eng_verb = infl.conjugate(eng_verb, \
                                infl.PRESENT, aspect = infl.PROGRESSIVE, \
                                person = sbj_person, number = sbj_number)
                            keep_verb = infl.conjugate("keep", infl.PAST, \
                                person = sbj_person, number = sbj_number)

                            eng_verb = keep_verb
                            after_verb = f"{pres_part_eng_verb} {after_verb}"

                    # If a direct object participant is present and the sense
                    # contains an 'O', 'something', or 'someone' placeholder,
                    # replace the placeholder with the nearest English
                    # equivalent of that direct object form.
                    if 'DObjForm' in participants: 
                        # The human plural nominalizer -ná "the ones that" can
                        # nominalize 3SG direct objects (e.g., yisʔín-ná "the
                        # ones that I saw", yiyíghón-ná "the ones that he/she/
                        # it killed", etc.).  In these cases, we can remove the
                        # placeholder for the direct object, keeping us from
                        # accidentally producing forms like "the ones that I
                        # saw him/her/it".
                        if 'NomzPl' in fst_rest and \
                            participants['DObjPerson'] == 3 and \
                            participants['DObjNumber'] == 'singular':
                            after_verb = re.sub(r'(O|something|someone)', '',
                                after_verb)
                        else:
                            after_verb_parts = after_verb.split(' ')
                            if 'O' in after_verb_parts:
                                after_verb = after_verb.replace('O', \
                                    participants['DObjForm'])
                            elif 'self' in after_verb_parts and \
                                  expand_placeholders:
                                after_verb = after_verb.replace('self', \
                                    participants['DObjForm'])
                            elif 'something' in after_verb_parts:
                                after_verb = after_verb.replace('something', \
                                    participants['DObjForm'])
                            elif 'someone' in after_verb_parts:
                                after_verb = after_verb.replace('someone', \
                                    participants['DObjForm'].replace(\
                                    'something', 'someone'))

                    # Likewise, but for oblique objects and an 'IO' placeholder.
                    if 'IObjForm' in participants: 
                        # The human plural nominalizer -ná "the ones that" can
                        # nominalize 3SG indirect direct objects (e.g.,
                        # mádzásnì-ná "the ones that I thought it was").
                        #
                        # As with the analogous direct object case above, we
                        # remove the placeholder for the indirect object here,
                        # thereby keeping us from accidentally producing forms
                        # like "the ones that I gave it to him/her/it".
                        if 'NomzPl' in fst_rest and \
                            participants['IObjPerson'] == 3 and \
                            participants['IObjNumber'] == 'singular':
                            after_verb = re.sub(r'(IO|something|someone|'\
                                'somethingP|someoneP)', '', after_verb)
                        else:
                            after_verb_parts = after_verb.split(' ')
                            if 'IO' in after_verb_parts:
                                after_verb = after_verb.replace('IO', \
                                    participants['IObjForm'])
                            elif 'selfP' in after_verb_parts and \
                                  expand_placeholders:
                                after_verb = after_verb.replace('selfP', \
                                    participants['IObjForm'])
                            # In ditransitive verbs, the lexical database uses
                            # 'somethingP' and 'someoneP' as placeholders for
                            # these oblique object forms.
                            elif 'somethingP' in after_verb_parts:
                                after_verb = after_verb.replace('somethingP', \
                                    participants['IObjForm'])
                            elif 'someoneP' in after_verb_parts:
                                after_verb = after_verb.replace('someoneP', \
                                    participants['IObjForm'].replace(\
                                    'something', 'someone'))
                            # In oblique object verbs, the lexical database
                            # allows 'self', 'something', and 'someone' to be
                            # used as placeholders for oblique object forms
                            # (since no direct object is present that would
                            # require disambiguation).
                            elif 'self' in after_verb_parts:
                                after_verb = after_verb.replace('self', \
                                    participants['IObjForm'])
                            elif 'something' in after_verb_parts:
                                after_verb = after_verb.replace('something', \
                                    participants['IObjForm'])
                            elif 'someone' in after_verb_parts:
                                after_verb = after_verb.replace('someone', \
                                    participants['IObjForm'].replace(\
                                    'something', 'someone'))

                    # This sense string is already specific to this aspect, so
                    # there is generally very little that we need to adjust
                    # beyond the person/number of the first (inflected) verb
                    # form to match what's given in the FST string.
                    #
                    # The one notable exception here is when the FST string is
                    # for a delayed future ("DF") verb form, which takes some
                    # (much) more extensive adjustment to get right.
                    if 'DF' in fst_rest:
                        after_verb = f'{after_verb} later on'
                        after_verb = after_verb.strip()

                        eng_verb_lemma = infl.lemma(eng_verb)

                        # IPFV: "will eat" --> "will eat later on", "be eating"
                        # --> "will be eating later on", "eats" --> "will eat
                        # later on"
                        if fst_aspect == 'IPFV':
                            if eng_verb == 'will':
                                pass
                            elif eng_verb_lemma == 'be':
                                eng_verb = 'will'
                                after_verb = 'be ' + after_verb
                            else:
                                eng_verb = 'will'
                                after_verb = f'{eng_verb_lemma} {after_verb}'

                        # PFV: "ate", "have eaten" --> "would have eaten later
                        # on"
                        #
                        # PFV-REP: "ate again and again" --> "would have eaten
                        # again and again later on"
                        elif fst_aspect == 'PFV' or fst_aspect == 'PFV-REP':
                            if eng_verb == 'have':
                                eng_verb = 'would'
                                after_verb = 'have ' + after_verb
                            else:
                                # For lexical verbs (e.g., "ate"), we need to
                                # get the corresponding past participle
                                # ("eaten").
                                past_participle = infl.conjugate(verb = \
                                    eng_verb_lemma, tense = infl.PAST, \
                                    aspect = infl.PROGRESSIVE)

                                eng_verb = 'would'
                                after_verb = \
                                    f'have {past_participle} {after_verb}'

                        # PROG: "is going along eating" --> "will be going
                        # along eating later on"
                        elif fst_aspect == 'PROG':
                            eng_verb = 'will'
                            after_verb = f'be {after_verb}'

                        # IPFV-REP: "eats again and again" --> "eats again and
                        # again later on"
                        elif fst_aspect == 'IPFV-REP':
                            pass

                        # IPFV-REPC: "eats" --> "eats later on", "keeps eating"
                        # --> "will keep eating later on"
                        elif fst_aspect == 'IPFV-REPC':
                            if eng_verb_lemma == 'keep':
                                eng_verb = 'will'
                                after_verb = f'keep {after_verb}'
                            else:
                                # Lexical verbs don't require any adjustment
                                # here.
                                pass

                        # PFV-REPC: "kept eating" --> "would have kept eating
                        # later on", "would eat" --> "would have eaten later
                        # on", "would keep eating" --> "would have kept eating
                        # later on"
                        elif fst_aspect == 'PFV-REPC':
                            if eng_verb_lemma == 'would':
                                # "keep", or some other (infinitival) lexical
                                # verb
                                lexical_verb = after_verb.split(' ')[0]
                                after_verb = \
                                    after_verb.removeprefix(\
                                    lexical_verb).strip()

                                # For lexical verbs (e.g., "ate"), we need to
                                # get the corresponding past participle
                                # ("eaten").
                                past_participle = infl.conjugate(verb = \
                                    lexical_verb, tense = infl.PAST, \
                                    aspect = infl.PROGRESSIVE)

                                after_verb = \
                                    f'would have {past_participle} {after_verb}'
                            else:
                                past_participle = infl.conjugate(verb = \
                                    eng_verb_lemma, tense = infl.PAST, \
                                    aspect = infl.PROGRESSIVE)

                                eng_verb = 'would'
                                after_verb = \
                                    f'have {past_participle} {after_verb}'

                        # POT: "may eat" --> "may eat later on", "might eat"
                        # --> "might eat later on"
                        elif fst_aspect == 'POT':
                            # No adjustment necessary.
                            pass

                    # Adjust the form of the verb to reflect the person and
                    # number of the (nearest English translation equivalent)
                    # subject.
                    #
                    # (infl.tenses takes a verb and returns a list of possible
                    # tenses that it could be in, where each tense is
                    # represented as a tuple of (tense, subject_person,
                    # subject_number, mood, aspect).)
#                    verb = infl.conjugate(verb = infl.lexeme(eng_verb)[0], \
                    verb = infl.conjugate(verb = infl.lemma(eng_verb), \
                        tense = infl.tenses(eng_verb)[0][0], \
                        person = sbj_person, number = sbj_number)

                    eng_phrase = f'{sbj_form} {verb} {after_verb}'.strip()

                    # Handle suffixes and enclitics (other than -i delayed
                    # future, which is implemented above).
                    if 'Relz' in fst_rest:
                        # The relativizer -í can appear with verb phrases in
                        # any aspect/superaspect and person-number inflection
                        # with the meaning "(the fact) that" (i.e., creating
                        # a nominal out of a verbal state or event).
                        phr = f'the fact that {eng_phrase}'
                        if not phr in english:
                            english.append(phr)

                    elif 'Nomz' in fst_rest or 'NomzA' in fst_rest:
                        # Nominalizations with -í create deverbal nominals that
                        # refer to one of the referents involved in the verbal
                        # action (e.g., with subjects, "the one who X").
                        # Likewise, nominalizations with -à produce deverbal
                        # nominals that refer to individuals, as well (e.g.,
                        # with subjects, "the one that X"), often in the
                        # context of personal names.  With both affixes, the
                        # nominalized participant must be 3SG.
                        phr = None
                        which = 'who' if 'Nomz' in fst_rest else 'that'

                        # If we're nominalizing a 3SG subject, replace the
                        # subject with "the one who/that".
                        if sbj_person == 3:
                            phr = \
                                f'the one {which} {verb} {after_verb}'.strip()
                            if not phr in english:
                                english.append(phr)

                        # Otherwise, if we're nominalizing a 3SG direct or in-
                        # direct object, then frame the resulting nominalization
                        # around that participant.
                        elif (participants.get('DObjPerson') == 3 and \
                              participants.get('DObjNumber') == 'singular') or \
                             (participants.get('IObjPerson') == 3 and \
                              participants.get('IObjNumber') == 'singular'):
                            phr = f'the one {which} {sbj_form} {verb} '\
                                  f'{after_verb}'.strip()

                            # TODO: do we need to worry about how to translate
                            # distributives here? (e.g., dàgùschùdà "the one
                            # who caught each and every one of them")

                        if phr and not phr in english:
                            english.append(phr)

                    elif 'NomzPl' in fst_rest:
                        # Nominalizations with -ná all refer to plural groups
                        # of human beings ("the ones that X").  The nominalized
                        # participant must be in the third person.
                        if sbj_person == 3 or \
                           participants.get('DObjPerson') == 3 or \
                           participants.get('IObjPerson') == 3:

                            # If we're nominalizing a 3SG direct or indirect
                            # object, then keep the verb form the way it's been
                            # inflected for this subject.
                            if participants.get('DObjPerson') == 3 or \
                               participants.get('IObjPerson') == 3:
                                phr = f'the ones that {sbj_form} '\
                                      f'{verb} {after_verb}'.strip()
                            # Otherwise, use the 3PL form (to fit with "the
                            # ones that" as a subject).
                            else:
                                verb = infl.conjugate(
                                    verb = infl.lexeme(eng_verb)[0],
                                    tense = infl.tenses(eng_verb)[0][0],
                                    person = 3, number = infl.PL)
                                phr = 'the ones that '\
                                      f'{verb} {after_verb}'.strip()

                            if is_distributive:
                                phr = f'all of {phr}'

                            if not phr in english:
                                english.append(phr)

                    else:
                        if eng_phrase not in english:
                            english.append(eng_phrase)

                    # TODO: Deal with remaining enclitics and suffixes!
                    # (EN/gu, EN/la, EN/gula, ...)

        english_senses = [(', '.join(sorted(subsense_phrases))).replace(\
            '  ', ' ') for subsense_phrases in english_senses]
        return sorted(english_senses)
