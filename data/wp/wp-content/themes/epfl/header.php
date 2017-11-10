<?php
/**
 * The header for our theme
 *
 * This is the template that displays all of the <head> section and everything up until <div id="content">
 *
 * @link https://developer.wordpress.org/themes/basics/template-files/#template-partials
 *
 * @package WordPress
 * @subpackage Twenty_Seventeen
 * @since 1.0
 * @version 1.0
 */

?><!DOCTYPE html>
<html <?php language_attributes(); ?> class="no-js no-svg">
<head>
<meta charset="<?php bloginfo( 'charset' ); ?>">
<meta name="viewport" content="width=device-width, initial-scale=1" data-header-version="0.26.0">
<link rel="profile" href="http://gmpg.org/xfn/11">

<script type="text/javascript" src="//www.epfl.ch/js/jquery-epfl.min.js"></script>
<script type="text/javascript">jQuery.noConflict();</script>
<script type="text/javascript" src="//www.epfl.ch/js/globalnav.js"></script>

<link rel="stylesheet" href="https://static.epfl.ch/v0.26.0/styles/epfl-built.css">

<?php wp_head(); ?>
</head>

<body <?php body_class(); ?>>
<div id="page" class="site">
	<a class="skip-link screen-reader-text" href="#content"><?php _e( 'Skip to content', 'epfl' ); ?></a>

	<div class="header-top wrap">
		<?php
		/* Configuration */
		$allowed_langs = array('en', 'fr');
		$default_lang = 'en';
		/* If Polylang installed */
		if(function_exists('pll_current_language'))
		{
			/* Get current lang */
			 $cur_lang = pll_current_language('slug');
			 /* Check if current lang is supported. If not, use default lang*/
			 if(!in_array($cur_lang, $allowed_langs)) $cur_lang=$default_lang;

		}
		else /* Polylang not installed */
		{
			$cur_lang = $default_lang;
		}



		?>
  	<header id="epfl-header" class="site-header epfl" data-ajax-header="https://static.epfl.ch/latest/includes/epfl-header.<?php echo $cur_lang; ?>.html"></header>
	</div><!-- .header-top -->

	<header id="masthead" class="site-header" role="banner">

		<section class="page-tools">
  		<div class="wrap">

  		<?php if ( !is_front_page() ): ?>
  		<div class="breadcrumb"><?php get_breadcrumb(); ?></div>
  		<?php endif; ?>

  		<div class="lang">
    		<ul class="language-switcher">
    		  <?php if(function_exists('pll_the_languages'))pll_the_languages(array('hide_if_no_translation'=>1)); ?>
    		</ul>
  		</div>

  		</div><!-- .wrap -->
		</section><!-- .page-tools -->

		<div class="custom-header">
  		<?php get_template_part( 'template-parts/header/site', 'branding' ); ?>
    </div><!-- .custom-header -->

		<?php if ( has_nav_menu( 'top' ) ) : ?>
			<div class="navigation-top">
				<div class="wrap">
					<?php get_template_part( 'template-parts/navigation/navigation', 'top' ); ?>
				</div><!-- .wrap -->
			</div><!-- .navigation-top -->
		<?php endif; ?>

	</header><!-- #masthead -->

	<div class="site-content-contain">
		<div id="content" class="site-content">

  		<?php if ( is_single() || is_page() || is_home() ) : ?>

  		<section class="toolbar wrap">
    		<?php if ( function_exists( 'ADDTOANY_SHARE_SAVE_KIT' ) ) : ?>
    		<div class="social-share">
      		<p class="label"><?php _e( 'Share', 'epfl' ); ?>:</p>
    		  <?php ADDTOANY_SHARE_SAVE_KIT(); ?>
    		</div><!-- .social-share -->
    		<?php endif; ?>
  		</section><!-- .toolbox -->

      <?php endif; ?>
