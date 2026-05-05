"""
RCF Plugins — All 30 source plugins for recruiter contact discovery.

Plugin categories:
  - API plugins (11): External REST/GraphQL APIs
  - Scraping plugins (9): HTML/browser scraping sources
  - Executive search plugins (5): Big-5 executive search firms
  - Local/utility plugins (5): Permutation, OSINT, UAE-specific
"""

from .hunter import HunterPlugin
from .apollo import ApolloPlugin
from .seamless_ai import SeamlessAIPlugin
from .snov import SnovPlugin
from .rocketreach import RocketReachPlugin
from .zerobounce import ZeroBouncePlugin
from .abstract_api import AbstractAPIPlugin
from .people_data_labs import PeopleDataLabsPlugin
from .google_places import GooglePlacesPlugin
from .greenhouse import GreenhousePlugin
from .lever import LeverPlugin
from .linkedin import LinkedInPlugin
from .dmcc_directory import DMCCDirectoryPlugin
from .expatriates import ExpatriatesPlugin
from .dubizzle import DubizzlePlugin
from .uae_yellow_pages import UAEYellowPagesPlugin
from .bayt import BaytPlugin
from .gulf_talent import GulfTalentPlugin
from .naukrigulf import NaukrigulfPlugin
from .facebook_groups import FacebookGroupsPlugin
from .heidrick_and_struggles import HeidrickAndStrugglesPlugin
from .korn_ferry import KornFerryPlugin
from .spencer_stuart import SpencerStuartPlugin
from .egon_zehnder import EgonZehnderPlugin
from .russell_reynolds import RussellReynoldsPlugin
from .email_permutator import EmailPermutatorPlugin
from .google_dorking import GoogleDorkingPlugin
from .whatsapp_checker import WhatsAppCheckerPlugin
from .uae_phone_detector import UAEPhoneDetectorPlugin
from .arabic_name_normalizer import ArabicNameNormalizerPlugin

__all__ = [
    "HunterPlugin",
    "ApolloPlugin",
    "SeamlessAIPlugin",
    "SnovPlugin",
    "RocketReachPlugin",
    "ZeroBouncePlugin",
    "AbstractAPIPlugin",
    "PeopleDataLabsPlugin",
    "GooglePlacesPlugin",
    "GreenhousePlugin",
    "LeverPlugin",
    "LinkedInPlugin",
    "DMCCDirectoryPlugin",
    "ExpatriatesPlugin",
    "DubizzlePlugin",
    "UAEYellowPagesPlugin",
    "BaytPlugin",
    "GulfTalentPlugin",
    "NaukrigulfPlugin",
    "FacebookGroupsPlugin",
    "HeidrickAndStrugglesPlugin",
    "KornFerryPlugin",
    "SpencerStuartPlugin",
    "EgonZehnderPlugin",
    "RussellReynoldsPlugin",
    "EmailPermutatorPlugin",
    "GoogleDorkingPlugin",
    "WhatsAppCheckerPlugin",
    "UAEPhoneDetectorPlugin",
    "ArabicNameNormalizerPlugin",
]
