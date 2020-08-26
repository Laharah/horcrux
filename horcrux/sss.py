"""Custom Shamir Secret Sharing Module using a modifed version of the SLIP-0039 standard

https://github.com/satoshilabs/slips/blob/master/slip-0039.md


curve generation:
    choose points where f(255) == secret & f(254) == digest(secret) and threshold-2 
    random points. construct the curve going throuhg those points, and distribute shares
    from that curve.


"""
