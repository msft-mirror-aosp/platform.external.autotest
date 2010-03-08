// Copyright (c) 2010 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// List of tasks to accomplish
var URLS = new Array();

var ViewGDoc = ('http://docs.google.com/RawDocContents?action=fetch&' +
                'justBody=false&revision=_latest&editMode=true&docID=');

var tasks = [
  {
    // Chrome browser window 1. This window remains open for the entire test.
    'type': 'window',
    start: 0,
    duration: 60 * 60 * 1000,
    tabs: [
     'http://www.cnn.com',
     'http://news.google.com',
     'http://finance.yahoo.com',
     'http://clothing.shop.ebay.com/Womens-Shoes-/63889/i.html',
     'http://www.facebook.com'
    ]
  },
  {
    // Page cycle through popular external websites for 36 minutes
    type: 'cycle',
    name: 'web',
    start: 0,
    duration: 36 * 60 * 1000,
    delay: 60 * 1000, // A minute on each page
    timeout: 10 * 1000,
    focus: true,
    urls: URLS,
  },
  {
    // After 36 minutes, actively read e-mail for 12 minutes
    type: 'cycle',
    name: 'email',
    start: 36 * 60 * 1000 + 1 * 1000,
    duration: 12 * 60 * 1000 - 1 * 1000,
    delay: 60 * 1000, // A minute on each page
    timeout: 10 * 1000,
    focus: true,
    urls: [
       'http://gmail.com',
       'http://mail.google.com'
    ],
  },
  {
    // After 36 minutes, start streaming audio (background tab), total playtime
    // 12 minutes
    type: 'cycle',
    name: 'audio',
    start: 36 * 60 * 1000,
    duration: 12 * 60 * 1000,
    delay: 12 * 60 * 1000,
    timeout: 10 * 1000,
    focus: false,
    urls: [
      'http://www.bbc.co.uk/iplayer/console/worldservice/',
      'http://www.npr.org/templates/player/mediaPlayer.html?action=3&t=live1',
      'http://www.cbc.ca/radio2/channels/popup.html?stream=classical'
    ]
  },
  {
    // After 48 minutes, play with Google Docs for 6 minutes
    type: 'cycle',
    name: 'docs',
    start: 48 * 60 * 1000,
    duration: 12 * 60 * 1000,
    delay: 60 * 1000, // A minute on each page
    timeout: 10 * 1000,
    focus: true,
    urls: [
       ViewGDoc + '0AaLGACl774zLZGRuYzlibWtfMXJzbmdoamcy',
       ViewGDoc + '0AaLGACl774zLZGRuYzlibWtfMGRkcmY4emNu'
    ],
  },
  {
    // After 54 minutes, watch Google IO for 6 minutes
    type: 'window',
    name: 'video',
    start: 54 * 60 * 1000,
    duration: 6 * 60 * 1000,
    focus: true,
    tabs: [
      'http://www.youtube.com/watch_popup?v=ecI_hCBGEIM'
    ]
  },
];


// List of URLs to cycle through
var u_index = 0;
URLS[u_index++] = 'http://www.google.com';
URLS[u_index++] = 'http://www.yahoo.com';
URLS[u_index++] = 'http://www.facebook.com';
URLS[u_index++] = 'http://www.youtube.com';
URLS[u_index++] = 'http://www.wikipedia.org';
URLS[u_index++] = 'http://www.amazon.com';
URLS[u_index++] = 'http://www.msn.com';
URLS[u_index++] = 'http://www.bing.com';
URLS[u_index++] = 'http://www.blogspot.com';
URLS[u_index++] = 'http://www.microsoft.com';
URLS[u_index++] = 'http://www.myspace.com';
URLS[u_index++] = 'http://www.go.com';
URLS[u_index++] = 'http://www.walmart.com';
URLS[u_index++] = 'http://www.about.com';
URLS[u_index++] = 'http://www.target.com';
URLS[u_index++] = 'http://www.aol.com';
URLS[u_index++] = 'http://www.mapquest.com';
URLS[u_index++] = 'http://www.ask.com';
URLS[u_index++] = 'http://www.craigslist.org';
URLS[u_index++] = 'http://www.wordpress.com';
URLS[u_index++] = 'http://www.answers.com';
URLS[u_index++] = 'http://www.paypal.com';
URLS[u_index++] = 'http://www.imdb.com';
URLS[u_index++] = 'http://www.bestbuy.com';
URLS[u_index++] = 'http://www.ehow.com';
URLS[u_index++] = 'http://www.photobucket.com';
URLS[u_index++] = 'http://www.cnn.com';
URLS[u_index++] = 'http://www.chase.com';
URLS[u_index++] = 'http://www.att.com';
URLS[u_index++] = 'http://www.sears.com';
URLS[u_index++] = 'http://www.weather.com';
URLS[u_index++] = 'http://www.apple.com';
URLS[u_index++] = 'http://www.zynga.com';
URLS[u_index++] = 'http://www.adobe.com';
URLS[u_index++] = 'http://www.bankofamerica.com';
URLS[u_index++] = 'http://www.zedo.com';
URLS[u_index++] = 'http://www.flickr.com';
URLS[u_index++] = 'http://www.shoplocal.com';
URLS[u_index++] = 'http://www.twitter.com';
URLS[u_index++] = 'http://www.cnet.com';
URLS[u_index++] = 'http://www.verizonwireless.com';
URLS[u_index++] = 'http://www.kohls.com';
URLS[u_index++] = 'http://www.bizrate.com';
URLS[u_index++] = 'http://www.jcpenney.com';
URLS[u_index++] = 'http://www.netflix.com';
URLS[u_index++] = 'http://www.fastclick.net';
URLS[u_index++] = 'http://www.windows.com';
URLS[u_index++] = 'http://www.questionmarket.com';
URLS[u_index++] = 'http://www.nytimes.com';
URLS[u_index++] = 'http://www.toysrus.com';
URLS[u_index++] = 'http://www.allrecipes.com';
URLS[u_index++] = 'http://www.overstock.com';
URLS[u_index++] = 'http://www.comcast.net';

