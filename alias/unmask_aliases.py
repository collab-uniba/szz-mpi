import logging
import os
import pickle
import sys
from collections import Counter
from itertools import combinations, product
from szz.SzzContributor import SzzContributor
import loggingcfg
import utils.utility as utility

import regex

from alias import Alias
from csvmanager import CsvWriter

d_alias_map = {}
clusters = {}
labels = {}

USR_FAKE = 'FAKE'
USR_REAL = 'REAL'

EMAIL = 'EMAIL'
COMP_EMAIL_PREFIX = 'COMP_EMAIL_PREFIX'
SIMPLE_EMAIL_PREFIX = 'SIMPLE_EMAIL_PREFIX'
PREFIX_LOGIN = 'PREFIX_LOGIN'
PREFIX_NAME = 'PREFIX_NAME'
LOGIN_NAME = 'LOGIN_NAME'
FULL_NAME = 'FULL_NAME'
SIMPLE_NAME = 'SIMPLE_NAME'
LOCATION = 'LOCATION'
DOMAIN = 'EMAIL_DOMAIN'
TWO = 'TWO_OR_MORE_RULES'

THR_MIN = 1
THR_MAX = 10

log = loggingcfg.initialize_logger('SZZ-UNMASK', console_level=logging.INFO)


def merge(a, b, rule):
    if a in d_alias_map:
        if b in d_alias_map:
            labels[d_alias_map[a]].append(rule)
        else:
            d_alias_map[b] = d_alias_map[a]
            clusters[d_alias_map[a]].add(b)
            labels[d_alias_map[a]].append(rule)
    else:
        if b in d_alias_map:
            d_alias_map[a] = d_alias_map[b]
            clusters[d_alias_map[b]].add(a)
            labels[d_alias_map[b]].append(rule)
        else:
            d_alias_map[a] = a
            d_alias_map[b] = a
            clusters[a] = {a, b}
            labels[a] = [rule]


def main(input_dir_path: str, out_dir_path: str):
    log.info("Input dir: %s; out_dir: %s", input_dir_path, out_dir_path)
    try:
        out_dir = os.path.abspath(out_dir_path)
    except IndexError:
        out_dir = os.path.abspath('./')
    out_dir = os.path.join(out_dir, 'idm')
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'dict'), exist_ok=True)

    fakeusr_rex = regex.compile(r'\A[A-Z]{8}$')

    unmask = {}

    w_log = CsvWriter(csv_file=os.path.join(out_dir, 'idm_log.csv'))
    writer = CsvWriter(csv_file=os.path.join(out_dir, 'idm_map.csv'))
    w_maybe = CsvWriter(csv_file=os.path.join(out_dir, 'idm_maybe.csv'))

    idx = 0
    step = 100000
    curidx = step

    aliases = {}

    # Helper structures
    d_email_uid = {}
    d_uid_email = {}

    d_prefix_uid = {}
    d_uid_prefix = {}

    d_comp_prefix_uid = {}
    d_uid_comp_prefix = {}

    d_uid_domain = {}
    d_domain_uid = {}

    d_name_uid = {}
    d_uid_name = {}

    d_login_uid = {}
    d_uid_login = {}

    #df = pd.read_csv(input_dir_path, index_col=False, na_filter=False)
    df = utility.read_from_folder(input_dir_path, "*contributors.csv")

    users = [SzzContributor(getattr(row, "CONTRIBUTOR_ID"), getattr(row, "NAME"), getattr(row, "EMAIL")) for row in df.itertuples(index=False)]
    log.info("Users to parse: %d", len(users))

    for user in users:
        uid = user.id
        login = user.name
        name = user.name
        email = user.email

        if name is "github" and email is "noreply@github.com":
            continue

        unmask[uid] = uid

        m = fakeusr_rex.search(login)
        if m is not None:
            record_type = USR_FAKE
        else:
            record_type = USR_REAL

        # a = Alias(record_type, uid, login, name, email, location, user_type)
        a = Alias(record_type, uid, login, name, email)
        aliases[uid] = a

        # - email
        d_uid_email[a.uid] = a.email
        if a.email is not None:
            d_email_uid.setdefault(a.email, {a.uid})
            d_email_uid[a.email].add(a.uid)

        # - prefix
        d_uid_prefix[a.uid] = a.email_prefix
        d_uid_comp_prefix[a.uid] = a.email_prefix
        if a.email_prefix is not None:
            if len(a.email_prefix.split('.')) > 1 or len(a.email_prefix.split('_')) > 1:
                d_comp_prefix_uid.setdefault(a.email_prefix, {a.uid})
                d_comp_prefix_uid[a.email_prefix].add(a.uid)
            else:
                d_prefix_uid.setdefault(a.email_prefix, {a.uid})
                d_prefix_uid[a.email_prefix].add(a.uid)

        # - domain
        d_uid_domain[a.uid] = a.email_domain
        if a.email_domain is not None:
            d_domain_uid.setdefault(a.email_domain, {a.uid})
            d_domain_uid[a.email_domain].add(a.uid)

        # - login
        d_uid_login[a.uid] = a.login
        if a.login is not None:
            d_login_uid.setdefault(a.login, set([a.uid]))
            d_login_uid[a.login].add(a.uid)

            if a.record_type == USR_REAL:
                d_login_uid.setdefault(a.login.lower(), set([a.uid]))
                d_login_uid[a.login.lower()].add(a.uid)

        # - name
        d_uid_name[a.uid] = a.name
        if a.name is not None and len(a.name):
            d_name_uid.setdefault(a.name, {a.uid})
            d_name_uid[a.name].add(a.uid)

            if len(a.name.split(' ')) == 1:
                d_name_uid.setdefault(a.name.lower(), {a.uid})
                d_name_uid[a.name.lower()].add(a.uid)

        idx += 1
        if idx >= curidx:
            log.info(curidx / step, '/ 30')
            curidx += step

    log.info('Done: helpers')

    clues = {}

    for email, set_uid in d_email_uid.items():
        if len(set_uid) > THR_MIN:
            for a, b in combinations(sorted(set_uid, key=lambda uid: uid), 2):
                clues.setdefault((a, b), [])
                clues[(a, b)].append(EMAIL)
    log.info('Done: email')

    for prefix, set_uid in d_comp_prefix_uid.items():
        if THR_MIN < len(set_uid) < THR_MAX:
            if len(prefix) >= 3:
                for a, b in combinations(sorted(set_uid, key=lambda uid: uid), 2):
                    clues.setdefault((a, b), [])
                    clues[(a, b)].append(COMP_EMAIL_PREFIX)
    log.info('Done: comp email prefix')

    for prefix, set_uid in d_prefix_uid.items():
        if THR_MIN < len(set_uid) < THR_MAX:
            if len(prefix) >= 3:
                for a, b in combinations(sorted(set_uid, key=lambda uid: uid), 2):
                    clues.setdefault((a, b), [])
                    clues[(a, b)].append(SIMPLE_EMAIL_PREFIX)
    log.info('Done: email prefix')

    for prefix in set(d_prefix_uid.keys()).intersection(set(d_login_uid.keys())):
        if len(d_prefix_uid[prefix]) < THR_MAX:
            for a, b in product(sorted(d_login_uid[prefix], key=lambda uid: uid), sorted(d_prefix_uid[prefix],
                                                                                              key=lambda uid:
                                                                                                  uid)):
                if a < b:
                    clues.setdefault((a, b), [])
                    if SIMPLE_EMAIL_PREFIX not in clues[(a, b)]:
                        clues[(a, b)].append(PREFIX_LOGIN)
    log.info('Done: prefix=login')

    for prefix in set(d_prefix_uid.keys()).intersection(set(d_name_uid.keys())):
        if len(d_prefix_uid[prefix]) < THR_MAX and len(d_name_uid[prefix]) < THR_MAX:
            for a, b in product(sorted(d_name_uid[prefix], key=lambda uid: uid), sorted(d_prefix_uid[prefix],
                                                                                             key=lambda uid: uid)):
                if a < b:
                    clues.setdefault((a, b), [])
                    if SIMPLE_EMAIL_PREFIX not in clues[(a, b)]:
                        clues[(a, b)].append(PREFIX_NAME)

    log.info('Done: prefix=name')

    for prefix in set(d_login_uid.keys()).intersection(set(d_name_uid.keys())):
        if len(d_name_uid[prefix]) < THR_MAX:
            for a, b in product(sorted(d_name_uid[prefix], key=lambda uid: uid), sorted(d_login_uid[prefix],
                                                                                             key=lambda uid: uid)):
                if a < b:
                    clues.setdefault((a, b), [])
                    if SIMPLE_EMAIL_PREFIX not in clues[(a, b)]:
                        clues[(a, b)].append(LOGIN_NAME)
    log.info('Done: login=name')

    #    print d_name_uid.items()
    for name, set_uid in d_name_uid.items():
        if len(set_uid) > THR_MIN and len(set_uid) < THR_MAX:
            if len(name.split(' ')) > 1:
                for a, b in combinations(sorted(set_uid, key=lambda uid: uid), 2):
                    clues.setdefault((a, b), [])
                    clues[(a, b)].append(FULL_NAME)
            #                    print a,b,FULL_NAME
            else:
                for a, b in combinations(sorted(set_uid, key=lambda uid: uid), 2):
                    clues.setdefault((a, b), [])
                    clues[(a, b)].append(SIMPLE_NAME)

    log.info('Done: full/simple name')

    for domain, set_uid in d_domain_uid.items():
        if THR_MIN < len(set_uid) < THR_MAX:
            for a, b in combinations(sorted(set_uid, key=lambda uid: uid), 2):
                clues.setdefault((a, b), [])
                clues[(a, b)].append(DOMAIN)
    log.info('Done: email domain')

    for (a, b), list_clues in sorted(clues.items(), key=lambda e: (e[0][0], e[0][1])):
        if EMAIL in list_clues:
            merge(a, b, EMAIL)
        elif len(list_clues) >= 2:
            for clue in list_clues:
                merge(a, b, clue)
        elif FULL_NAME in list_clues:
            merge(a, b, FULL_NAME)
        elif COMP_EMAIL_PREFIX in list_clues:
            merge(a, b, COMP_EMAIL_PREFIX)
    log.info('Done: clusters')

    for uid, member_uids in clusters.items():
        members = [aliases[m] for m in member_uids]

        # Count fake/real
        real = [m for m in members if m.record_type == USR_REAL]
        # with_location = [m for m in real if m.location is not None]

        # Count rules that fired
        cl = Counter(labels[uid])

        is_valid = False

        # If all have the same email there is no doubt
        if cl.get(EMAIL, 0) >= (len(members) - 1):
            is_valid = True
        # If all the REALs have the same email, assume all the FAKEs are this REAL
        elif len(Counter([m.email for m in real]).keys()) == 1:
            is_valid = True
        # If there is at most one real, at least two rules fired, and each rule applied to each pair
        elif len(real) <= 1 and len(cl.keys()) > 1 and min(cl.values()) >= (len(members) - 1):
            is_valid = True
        # At most one real, the only rule that fired is COMP_EMAIL_PREFIX or FULL_NAME
        elif len(real) <= 1 and len(cl.keys()) == 1 and \
                (cl.get(COMP_EMAIL_PREFIX, 0) or cl.get(FULL_NAME, 0)):
            is_valid = True
        # All with same full name and location / same full name and email domain
        elif cl.get(FULL_NAME, 0) >= (len(members) - 1) and \
                (cl.get(LOCATION, 0) >= (len(members) - 1) or cl.get(DOMAIN, 0) >= (len(members) - 1)):
            is_valid = True
        # All fake and same composite email prefix / same full name
        elif len(real) == 0 and \
                (cl.get(COMP_EMAIL_PREFIX, 0) >= (len(members) - 1) or cl.get(FULL_NAME, 0) >= (len(members) - 1)):
            is_valid = True
        else:
            # Split by email address if at least 2 share one
            if cl.get(EMAIL, 0):
                ce = [e for e, c in Counter([m.email for m in members]).items() if c > 1]
                for e in ce:
                    extra_members = [m for m in members if m.email == e]
                    # extra_with_location = [m for m in extra_real if m.location is not None]

                    # if len(extra_real):
                    #     if len(extra_with_location):
                    #         # Pick the one with the oldest account with location, if available
                    #         rep = sorted(extra_with_location, key=lambda m: int(m.uid))[0]
                    #     else:
                    #         # Otherwise pick the one with the oldest account
                    #         rep = sorted(extra_real, key=lambda m: int(m.uid))[0]
                    # else:
                    rep = sorted(extra_members, key=lambda m: m.uid)[0]

                    w_log.writerow([])
                    # w_log.writerow([rep.uid, rep.login, rep.name, rep.email, rep.location])
                    w_log.writerow([rep.uid, rep.name, rep.email])
                    for a in extra_members:
                        if a.uid != rep.uid:
                            # w_log.writerow([a.uid, a.login, a.name, a.email, a.location])
                            w_log.writerow([a.uid, a.name, a.email])
                            writer.writerow([a.uid, rep.uid])
                            unmask[a.uid] = rep.uid

            # -- added: Write also maybes to the alias map
            rep = sorted(members, key=lambda m: m.uid)[0]
            # -- end
            w_maybe.writerow([])
            w_maybe.writerow([str(cl.items())])
            for m in members:
                # -- added: added Write also maybes to the alias map
                if m.uid != rep.uid:
                    unmask[m.uid] = rep.uid
                    writer.writerow([m.uid, rep.uid])
                # -- end
                # w_maybe.writerow([m.uid, m.login, m.name, m.email, m.location])
                w_maybe.writerow([m.uid, m.name, m.email])

        if is_valid:
            # Determine group representative
            # if len(real):
            #    if len(with_location):
            #        # Pick the one with the oldest account with location, if available
            #        rep = sorted(with_location, key=lambda m: int(m.uid))[0]
            #    else:
            #        # Otherwise pick the one with the oldest account
            #        rep = sorted(real, key=lambda m: int(m.uid))[0]
            # else:
            rep = sorted(members, key=lambda m: m.uid)[0]

            w_log.writerow([])
            w_log.writerow([str(cl.items())])
            # w_log.writerow([rep.uid, rep.login, rep.name, rep.email, rep.location])
            w_log.writerow([rep.uid, rep.name, rep.email])
            for a in members:
                if a.uid != rep.uid:
                    # w_log.writerow([a.uid, a.login, a.name, a.email, a.location])
                    w_log.writerow([a.uid, a.name, a.email])
                    writer.writerow([a.uid, rep.uid])
                    unmask[a.uid] = rep.uid

    log.info("Unmasked size: %d", len(unmask))
    pickle.dump(unmask, open(os.path.join(out_dir, 'dict', 'aliasMap.dict'), 'wb'))


if __name__ == '__main__':
    input_file_dir = sys.argv[1]
    out_dir = sys.argv[2]
    main(input_file_dir, out_dir)
