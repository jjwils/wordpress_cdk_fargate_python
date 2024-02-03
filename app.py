#!/usr/bin/env python3
import os

import aws_cdk as cdk
from wpfargate.wordpress_albfargate_aurora_stack import WordpressFargateAuroraStack

app = cdk.App()
WordpressFargateAuroraStack(app, "WordpressFargateAuroraStack")

app.synth()
