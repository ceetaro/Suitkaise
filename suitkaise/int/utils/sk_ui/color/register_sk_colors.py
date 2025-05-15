 # -------------------------------------------------------------------------------------
# Copyright 2025 Casey Eddings
# Copyright (C) 2025 Casey Eddings
#
# This file is a part of the Suitkaise application, available under either
# the Apache License, Version 2.0 or the GNU General Public License v3.
#
# ~~ Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
#
#       Licensed under the Apache License, Version 2.0 (the "License");
#       you may not use this file except in compliance with the License.
#       You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing, software
#       distributed under the License is distributed on an "AS IS" BASIS,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#       See the License for the specific language governing permissions and
#       limitations under the License.
#
# ~~ GNU General Public License, Version 3 (http://www.gnu.org/licenses/gpl-3.0.html)
#
#       This program is free software: you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation, either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# -------------------------------------------------------------------------------------

# suitkaise/int/utils/sk_ui/color/register_sk_colors.py

"""
Register default SK colors for the SKColorRegistry.

"""


def register_sk_colors() -> None:
    """
    Register the default SK colors in the SKColorRegistry.
    
    """
    from suitkaise.int.utils.sk_ui.color.sk_color import SKColorRegistry
    creg = SKColorRegistry.get_instance()

    suitkaise_colors = {
        # shades of black
        "Black": "#000000",
        "Black 2": "#1B1B1B",
        "Black 3": "#100C08",
        "Charcoal": "#36454F",
        "Jet Black": "#343434",
        "Obsidian": "#0D031B",
        "Matte Black": "#2B2B2B",
        "Dark Charcoal": "#333333",
        "Dark Mountain Green": "#232B2B",
        "Dark Jungle Green": "#1A2421",
        "Black Olive": "#3B3C36",
        "Onyx": "#0F0F0F",
        "Licorice": "#1A1A1A",
        "Midnight Black": "#2C3539",
    
        # shades of gray
        "Gray": "#808080",
        "Light Gray": "#D4D4D4",
        "Dark Gray": "#A9A9A9",
        "Gunmetal": "#2C3539",
        "Space Gray": "#4B5454",
        "Outer Space": "#414A4C",
        "Slate Gray": "#708090",
        "Arsenic": "#3B444B",
        "Ash Gray": "#B2BEB5",
        "Battleship Gray": "#848482",
        "Gray Coral": "#54626F",
        "Light Charcoal": "#D3D3D3",
        "Blue Gray": "#98AFC7",
        "Cadet Gray": "#91A3B0",
        "Carbon Gray": "#625D5D",
        "Copper Gray": "#98817B",
        "Cool Blue Gray": "#9090C0",
        "Davy's Gray": "#555555",
        "Warp Space": "#4A646C",
        "Cloud Gray": "#DCDCDC",
        "Overcast Gray": "#B4B6B4",
        "Dolphin Gray": "#5C5858",
        "Gray Green": "#5E716A",
        "Wolf Gray": "#504A4B",
        "Light Slate Gray": "#6D7B8D",
        "Marengo": "#4C5866",
        "Nevada": "#666A6D",
        "Nickel": "#727472",
        "Tin": "#848482",
        "Silver": "#C0C0C0",
        "Platinum": "#E5E4E2",
        "Stone Gray": "#7D7B7A",
        "Mossy Gray": "#8B9A5B",
        "Scorpion": "#5E5E5E",
        "Steel": "#7C7B7A",
        "Smoke": "#738276",
        "Magnet": "#757575",
        "Sand Gray": "#928E85",
        "Xanadu": "#738678",
        "X11 Gray": "#BBBCB6",
        "Dark Silver": "#746D69",
        "Pastel Gray": "#CCCDC6",
        "Mist": "#F2F2F2",
        "Graphite": "#4B4E54",
        "Silk": "#B6B3A8",
        "Ice Gray": "#BEC3C6",

        # shades of white
        "White": "#FFFFFF",
        "Ghost": "#F8F8FF",
        "Snow": "#FFFAFA",
        "Snow Drift": "#F5FEFD",
        "Ivory": "#FFFFF0",
        "Floral White": "#FFFAF0",
        "Seashell": "#FFF5EE",
        "Linen": "#FAF0E6",
        "Old Lace": "#FDF5E6",
        "Light Cream": "#FAEBD7",
        "Parchment": "#F1E9D2",
        "Almond": "#EFDECD",
        "Beige": "#F5F5DC",
        "Bone": "#E3DAC9",
        "Alabaster": "#EDEAE0",
        "Birch": "#F0EEE4",
        "Rose White": "#FFFAFA",
        "Vista": "#FDFCFA",
        "Link White": "#ECF3F9",
        "Spring": "#F3F0E8",
        "Meringue": "#E6E8FA",
        "Cotton": "#F8F8FF",
        "Pearl": "#F6F1F4",
        "Vanilla": "#F3E5AB",
        "Harpy": "#EBF5F0",
        "Coconut": "#FFF1E6",
        "Himalaya": "#F8EEEC",
        "Chalk": "#F7F7F7",
        "Frost": "#FCFBFC",
        "Rice": "#FAF5EF",
        "Dove White": "#F0EFE7",
        "Wisp": "#EAE8E1",
        "Steam": "#F0EBE4",
        "Diamond": "#F0F8FF",
        "Oyster": "#E3DFD2",
        "Off White": "#F8F8F0",
        "Azure White": "#F0FFFF",
        "Mercury": "#E7E7E7",
        "Bubble": "#E7FEFF",
        "Mirage": "#FDF9EF",
        "Wash": "#FEFFFC",
        "White Shadow": "#EEF1EA",
        "Rough Ceramic": "#EFECE4",
        "Fine Ceramic": "#FCFFF8",
        "Swan": "#FCFCFC",

        # shades of red
        "Red": "#FF0000",
        "Dark Red": "#8B0000",
        "Light Red": "#FF7F7F",
        "Crimson": "#DC143C",
        "Scarlet": "#FF2400",
        "Native Red": "#CD5C5C",
        "Barn": "#7C0A02",
        "Chili": "#C21807",
        'Ruby': '#E0115F',
        "Maroon": "#800000",
        "Red Brick": "#B22222",
        "Brick": "#7E2811",
        "Redwood": "#A45A52",
        "Carmine": "#960018",
        "Dark Hot Pink": "#EA3C53",
        "Vermilion": "#7E191B",
        "Cherry": "#DE3163",
        "Strawberry": "#FF3F34",
        "Raspberry": "#D21F3C",
        "Persia": "#CA3433",
        "Hibiscus": "#B43757",
        "US Flag's Red": "#BF0A30",
        "Ferrari Red": "#FF2800",
        "Red Orange": "#FF4500",
        "Sangria": "#5E1914",
        "Mahogany": "#420D09",
        "Burgundy": "#8D021F",
        "Rust": "#933A16",
        "Salmon": "#FA8072",
        "Light Salmon": "#FFA07A",
        "Dark Salmon": "#E9967A",
        "Coral Red": "#FF4040",
        "Light Coral": "#F08080",
        "Tomato": "#FF6347",
        "Pale Violet Pink": "#DB7093",
        "Light Hot Pink": "#FB607F",

        # shades of orange
        "Orange": "#FFA500",
        "Dark Orange": "#FF8C00",
        "Light Orange": "#FFB347",
        "Pumpkin": "#F5761A",
        "Yellow Orange": "#FFA836",
        "Carrot": "#ED9121",
        "Aerospace Orange": "#FF4F00",
        "Spanish Orange": "#F06105",
        "Tangerine": "#F78702",
        "Saffron Orange": "#FFA52C",
        "Creamsicle": "#FFA07A",
        "Alloy": "#C35214",
        "Dim Vermilion": "#CF5B2E",
        "Pastel Orange": "#FEBA4F",
        "Orange Flame": "#E34A27",
        "Royal Orange": "#FF9944",
        "Cadmium": "#E6812F",
        "Rajah": "#FABA5F",
        "Peach": "#FFE5B4",
        "Light Apricot": "#FDD5B1",
        "Apricot": "#FBCEB1",

        # shades of pink
        "Pink": "#FFC0CB",
        "Light Pink": "#FFB6C1",
        "Dark Pink": "#D5006D",
        "Hot Pink": "#FF69B4",
        "Watermelon": "#FC6C85",
        "Flamingo": "#FC8EAC",
        "Pastel Pink": "#FFD1DC",
        "Sakura": "#FFB7C5",
        "Bubblegum": "#FFC1CC",
        "Rouge": "#A94064",
        "Neon Pink": "#FF6F61",
        "Blush": "#DE5D83",
        "Fuchsia": "#C154C1",
        "Mauve": "#E0B0FF",
        "Magenta": "#FF00FF",
        "Rose": "#FF007F",
        "Cherry Blossom": "#FFB3D9",
        "Carnation": "#FFA6C9",
        "Tulip": "#FF8E8E",
        "New York Pink": "#DD8374",
        "Pink Pearl": "#DDA0DD",


        # shades of yellow



        # shades of green
        # shades of blue
        # shades of purple
        # shades of brown


    }

    # Register the colors in the SKColorRegistry
    for color_name, color_value in suitkaise_colors.items():
        creg.register_suitkaise_color(color_name, color_value)
